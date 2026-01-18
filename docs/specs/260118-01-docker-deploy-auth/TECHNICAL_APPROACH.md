# 技术实现路径：Docker 部署（公网）+ 密码鉴权

> 对应 PRD：`docs/specs/260118-01-docker-deploy-auth/prd.md`

## 1. 目标与边界

### 1.1 目标（MVP 必须交付）

- 提供可在公网服务器部署的 Docker 方案（`Dockerfile` + `docker-compose.yml`），可一键启动。
- 后端容器监听 `0.0.0.0`，可被反代/外部访问。
- 数据持久化：SQLite（`data/ccg_gateway.db`）+ backups（`data/backups/`）+ 可选日志（`data/app.log`）。
- 应用层鉴权默认开启：覆盖
  - 管理 API：`/admin/v1/*`
  - 网关转发入口：`/{path:path}`
- 鉴权方式：单个共享 Token（Header Token），推荐请求头：`X-CCG-Token: <token>`。
- 规则：`X-CCG-Token` 仅用于客户端 -> 网关鉴权，不得向上游（Provider）透传。

### 1.2 明确不做（本次不包含）

- 桌面托盘/pywebview 模式的容器化。
- 多用户/多租户/权限系统。
- 自动签发证书（HTTPS 仅提供 Nginx 配置建议与指引）。

## 2. 现状盘点（基于当前代码）

### 2.1 后端路由入口与关键路径

- `backend/app/main.py`
  - `app.include_router(admin_router, prefix="/admin/v1")`
  - `/health` 探活接口存在，适合做容器健康检查。
  - `app.include_router(proxy_router)`：总是启用转发路由。
- `backend/app/api/proxy.py`
  - `@proxy_router.api_route("/{path:path}", methods=[...])`，全路径转发入口。
- `backend/app/services/proxy_service.py`
  - 负责把客户端请求转发到上游 Provider。
  - 会复制客户端 headers 并做过滤（`FILTERED_HEADERS`），随后为不同 CLI 类型写入 Provider 的鉴权头：
    - Gemini：`x-goog-api-key = provider.api_key`
    - Claude/Codex：`Authorization = Bearer {provider.api_key}`
  - 当前 debug log 会打印 `dict(request.headers)` 与转发 `headers`，存在泄露敏感头的风险（PRD R2）。

### 2.2 配置与持久化路径

- `backend/app/core/config.py`
  - 使用 `pydantic-settings` 从根目录 `.env` 读取（`env_file = get_env_file()`）。
  - `DATA_DIR = <repo_root>/data`，并在 import 时创建目录。
- `backend/app/core/database.py`
  - SQLite 文件固定为 `DATA_DIR/ccg_gateway.db`。
- `backend/app/services/backup_service.py`
  - 备份目录固定为 `DATA_DIR/backups`。

结论：容器内只要保证工作目录一致（例如 `/app`），并把 `/app/data` 以 volume 挂载，即可满足持久化要求。

## 3. 总体架构方案（Maintainability 优先）

PRD 推荐方案（D3）：前后端分容器 + Nginx 反代。为降低耦合与变更影响范围，本次采用「后端容器 + Nginx（包含前端静态文件）容器」的两容器形态：

- `ccg-backend`：FastAPI + Uvicorn，暴露 `7788`，同时支持公网直连（PRD D6）。
- `ccg-web`：Nginx
  - 提供 Web UI 静态资源（Vue dist）。
  - 仅反代管理接口 `/admin/v1/*`（以及可选 `/health`）到后端。

说明：
- MVP 不强制让 CLI 走 Nginx 的 80/443 入口；CLI 直接访问后端 `:7788` 即可。
- 若后续需要在同域同端口同时满足「SPA 路由 + 全路径转发」，Nginx 的 location 规则会变复杂（需要严格区分“前端路由”和“转发入口”）；建议作为后续增强项，不在 MVP 内强推。

### 3.1 容器网络与端口

- 外部：
  - `80/443 -> ccg-web`（UI + 管理 API 反代）
  - `7788 -> ccg-backend`（网关转发入口 + 管理 API，均鉴权）
- 内部：
  - `ccg-web -> ccg-backend:7788`（Docker network 直连）

### 3.2 数据卷与持久化

- 将宿主机目录 `./data` 挂载到 `ccg-backend:/app/data`。
- 持久化范围：
  - `data/ccg_gateway.db`
  - `data/backups/*`
  - `data/app.log`（当 `LOG_TO_FILE=1`）

## 4. 后端鉴权设计（SOLID + 可测试性）

<a id="ta-4-auth"></a>

<a id="ta-4-1-srp"></a>
### 4.1 模块边界与职责拆分（SRP/SoC）

新增安全模块，保证鉴权逻辑与业务路由、转发逻辑解耦：

- `app/security/`
  - `token_auth.py`
    - `TokenExtractor`：从请求提取 token（Header）
    - `TokenValidator`：校验 token（本次实现为共享静态 token）
    - `GatewayAuthDependency`：FastAPI dependency 入口（组合 extractor + validator）
- `app/api/deps.py`（或 `app/api/dependencies/auth.py`）
  - 暴露 `require_gateway_auth` 供 router 使用

依赖倒置（DIP）：router 依赖抽象的 `require_gateway_auth`，而不是直接依赖某个具体鉴权实现。

<a id="ta-4-2-config"></a>
### 4.2 配置项（可扩展、可测试）

在 `backend/app/core/config.py` 的 `Settings` 中新增：

- `CCG_AUTH_ENABLED: bool = True`
- `CCG_AUTH_TOKEN: str | None = None`
- `CCG_AUTH_HEADER_NAME: str = "X-CCG-Token"`（默认值固定，便于未来扩展）

规则：
- 当 `CCG_AUTH_ENABLED=true` 时，启动阶段必须校验 `CCG_AUTH_TOKEN` 非空；否则启动失败（Fail Fast）。
- 当 `CCG_AUTH_ENABLED=false` 时，鉴权依赖直接放行（仅用于内网/测试场景；生产默认开启）。

<a id="ta-4-3-coverage"></a>
### 4.3 覆盖范围（路由级依赖，避免全局副作用）

理由（Maintainability）：
- 全局 middleware 往往难以精确排除 `/health` 与未来公共路由；router dependency 更可控。

实现方式：

- 管理 API：在 `admin_router` 上统一加依赖
  - 方案 A：`admin_router = APIRouter(dependencies=[Depends(require_gateway_auth)])`
  - 或在 `main.py` include_router 时传 `dependencies=[Depends(...)]`
- 转发入口：在 `proxy_router` 上统一加依赖
  - `proxy_router = APIRouter(dependencies=[Depends(require_gateway_auth)])`

豁免：
- `/health` 不加依赖（用于探活）。

<a id="ta-4-3-route-order"></a>
#### 4.3.1 路由优先级与 catch-all 风险（必须验证）

当前后端存在两个 catch-all 路由来源：

- 代理转发：`backend/app/api/proxy.py` 的 `/{path:path}`（始终注册，用于 CLI/客户端转发）。
- SPA 静态服务：`backend/app/main.py` 的 `/{full_path:path}`（仅在 `frontend_dist` 存在时注册，用于桌面模式 serve dist）。

需要明确并验证以下不变量（否则可能出现“路由被吃掉”）：

- `/health` 必须在任何 catch-all 之前匹配成功，并且免鉴权。
- Web/Docker 部署模式下，后端不应注册 SPA 的 `/{full_path:path}`（即 `frontend_dist is None`），避免与 proxy catch-all 竞争。
- 若未来需要在同一进程同时启用 SPA 静态服务与 proxy 转发，必须通过注册顺序或更精细的路径划分避免冲突（MVP 不建议）。

测试要求（建议作为集成测试）：

- 访问 `/health`（不带 token）应返回 200，且不会落入 `/{path:path}` 触发鉴权。
- 访问 `/admin/v1/settings`（不带 token）应返回 401/403。
- 访问 `/{path:path}` 任意路径（不带 token）应返回 401/403。

### 4.4 状态码与错误语义

- 缺少 token：返回 `401 Unauthorized`。
- token 不匹配：返回 `403 Forbidden`。
- 返回 body 不暴露真实 token、也不泄露内部校验规则。

<a id="ta-4-5-no-forward"></a>
### 4.5 严禁向上游透传 `X-CCG-Token`

后端转发实现位于 `backend/app/services/proxy_service.py`，当前 `FILTERED_HEADERS` 未包含 `x-ccg-token`。

改动策略（最小影响范围）：
- 将 `x-ccg-token` 加入 `FILTERED_HEADERS`（与 hop-by-hop 过滤逻辑复用）。
- 在构建 `headers` 后再执行一次显式移除：`headers.pop("x-ccg-token", None)`，作为双保险。

<a id="ta-4-6-redaction"></a>
### 4.6 日志脱敏（避免泄露 token/provider key）

现状：`proxy_service.py` 的 debug log 会打印客户端与转发 headers，可能包含：
- `authorization`
- `x-goog-api-key`
- `x-ccg-token`

方案（SRP）：新增 `app/security/redaction.py`（或 `app/core/log_redaction.py`）提供纯函数：

- `redact_headers(headers: Mapping[str, str]) -> dict[str, str]`
  - 统一 mask 敏感 header：`authorization`、`x-goog-api-key`、`x-ccg-token`、`cookie`、`set-cookie`
  - 输出可安全用于日志

并在 debug log 前对 headers 做脱敏。

<a id="ta-5-frontend"></a>
## 5. 前端适配策略（最小改动 + 可回滚）

关键事实：`frontend/src/api/instance.ts` 的 axios 实例 `baseURL` 是 `/admin/v1`，一旦后端对 `/admin/v1/*` 开启鉴权，浏览器必须在请求中带上 `X-CCG-Token`。

MVP 建议两段式推进：

1) 先实现“无 UI 变更”的可用方案（最快闭环）
- 前端在 axios request interceptor 中从 `localStorage` 读取 token（例如 key：`ccg_gateway_token`），若存在则附加到 header。
- 部署文档明确告知：首次登录前通过浏览器控制台设置 token。

2) 再补齐“有 UI 的 token 输入/保存”（更好的 UX）
- 在 Settings/Config 页面提供输入框保存到 `localStorage`。
- 该改动涉及页面交互与视觉呈现，可作为后续独立 PR/迭代。

安全注意：
- 不要把 token 编译进前端静态文件（会被任何访问者获取）。

## 6. Docker 文件与 Compose 规划

<a id="ta-6-docker"></a>

<a id="ta-6-1-backend-dockerfile"></a>
### 6.1 `ccg-backend` Dockerfile（建议放 `backend/Dockerfile`）

核心点：
- 使用生产模式启动：`uvicorn app.main:app --host 0.0.0.0 --port ${GATEWAY_PORT}`。
- 通过环境变量/`.env` 注入配置：`GATEWAY_PORT`、`LOG_TO_FILE`、`CCG_AUTH_*`。
- 工作目录固定 `/app`，使 `.env` 与 `data/` 路径与代码逻辑一致。

<a id="ta-6-2-web"></a>
### 6.2 `ccg-web`（Nginx + Vue dist，多阶段构建）

建议采用多阶段构建：

- Stage 1（Node）：`pnpm install && pnpm build` 生成 `frontend/dist`
- Stage 2（Nginx）：
  - `COPY dist/ -> /usr/share/nginx/html`
  - Nginx 配置：
    - `location / { try_files $uri $uri/ /index.html; }`（SPA）
    - `location /admin/v1/ { proxy_pass http://ccg-backend:7788; ... }`
    - 可选：`location /health { proxy_pass http://ccg-backend:7788/health; }`

<a id="ta-6-3-compose"></a>
### 6.3 `docker-compose.yml`（建议放仓库根目录或 `deploy/docker-compose.yml`）

规划要点：
- `ccg-backend`：
  - `ports: ["7788:7788"]`
  - `volumes: ["./data:/app/data"]`
  - `environment` 或 `env_file: .env`
  - `healthcheck`：`GET http://localhost:7788/health`
- `ccg-web`：
  - `ports: ["80:80"]`（可选加 443）
  - `depends_on` backend

注意：
- `.env` 的加载位置要与 `config.py` 的 `get_env_file()` 一致；推荐 compose 通过 `env_file` 注入环境变量，避免依赖容器内 `.env` 文件存在。

## 7. 测试策略（可测试性要求）

### 7.1 单元测试（核心业务逻辑可独立测试）

- `TokenValidator`：
  - token 正确/错误/缺失时的行为
  - `CCG_AUTH_ENABLED=false` 时的放行行为
- `redact_headers`：
  - 确认敏感字段被 mask
  - 非敏感字段不变

### 7.2 集成测试（关键路径）

使用 `httpx.AsyncClient(app=app, base_url="http://test")`（或 FastAPI TestClient）覆盖：

- `/health`：不带 token 返回 200
- `/admin/v1/settings`：
  - 不带 token 返回 401/403
  - 带正确 token 返回 200
- `/{path:path}`：
  - 不带 token 返回 401/403
  - 带正确 token：
    - 若测试环境不配置 provider，可预期 503（但鉴权应通过）
    - 或在测试用例中写入一个 provider 数据，使 forward_request 能走通（更完整）

<a id="ta-7-3-smoke"></a>
### 7.3 部署冒烟测试（DoD 对齐 PRD 第 12 节）

- `docker compose up -d`
- `curl http://<host>:7788/health`
- `curl http://<host>:7788/admin/v1/settings`（无 token -> 401/403）
- `curl -H 'X-CCG-Token: <token>' http://<host>:7788/admin/v1/settings`（200）

<a id="ta-8-release"></a>
## 8. 迁移与发布步骤

- 步骤 1：后端引入鉴权依赖（默认开启）+ 头过滤 + 日志脱敏。
- 步骤 2：补齐前端 axios header 注入（先无 UI 版本，保证 UI 可用）。
- 步骤 3：补齐 Dockerfile + compose + Nginx 配置，完成 30 分钟可部署目标。
- 步骤 4：按 PRD 用例执行验收；如有需要，再补 UI token 输入能力。

## 9. 风险与缓解

- Token 泄露：
  - 缓解：支持快速更换 token（重启生效即可）；文档建议配合防火墙/IP 白名单/限流。
- 日志泄露敏感信息：
  - 缓解：统一 headers 脱敏；避免输出请求体中的敏感字段（必要时对 body 也做规则化截断/脱敏）。
- Nginx 同端口同时承载 SPA 与全路径转发导致路由冲突：
  - 缓解：MVP 先让 CLI 走 `:7788`；需要同端口时再引入更精细的路由分流策略（或使用子域名）。

## 10. 参考资料

- FastAPI Security Tools：APIKeyHeader（自定义 header 取值）
  - https://fastapi.tiangolo.com/reference/security/
- FastAPI Dependencies：路由级/全局依赖
  - https://fastapi.tiangolo.com/tutorial/dependencies/
  - https://fastapi.tiangolo.com/tutorial/dependencies/global-dependencies/
- FastAPI 在 decorator 中声明 dependencies（适合鉴权这类“只做校验不取返回值”的逻辑）
  - https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-in-path-operation-decorators/
- Docker + Nginx + FastAPI + Vue 示例（供 compose/nginx 结构参考）
  - https://github.com/Apfirebolt/fastapi-vue-boilerplate
