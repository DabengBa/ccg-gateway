## Review Summary
- 结论：请求修改（阻塞项 2）
- 风险概览：鉴权默认值与路由覆盖的边界、Docker/compose 启动可用性、测试的真实性与隔离性
- 验证记录：
  - 后端：`backend/.venv/Scripts/python -m pytest -q`（本机 9 passed）
  - 前端：`cd frontend; bun run build`（通过）
  - Docker：本机无法连接 Docker Engine（未能实际 build/run）

## 多视角评审矩阵

### 功能/产品
- 需求对齐：
  - 已实现：共享 Token 鉴权、/health 免鉴权、前端自动携带 Token、提供配置页输入框、compose 与文档。
  - 关键边界：当开启鉴权且未设置 Token 时“Fail Fast”符合 PRD。
- 异常路径：
  - 401/403 区分明确；错误信息未回显 token，符合“不泄露 token”。
- UX：
  - 配置页新增 token 输入框，并用 `type=password` + `show-password`，默认不明文展示。

### 架构/后端
- 模块职责：
  - `app/security/token_auth.py` 以 FastAPI dependency 形式提供鉴权，符合“高内聚/低耦合”。
  - `app/security/redaction.py` 抽为纯函数脱敏，便于复用与测试。
- 分层与耦合：
  - `admin_router` 与 `proxy_router` 在 router 级别挂载 Depends，避免全局 middleware，边界清晰。

### 前端/UI/可访问性
- 状态管理：
  - token 采用 `localStorage(ccg_gateway_token)`，axios 拦截器读取；配置页直接读写 localStorage。
- 可访问性：
  - 现有实现依赖 element-plus 组件；输入框可键盘聚焦，基本可用。
  - 建议：补充 token 的用途提示文案（tooltip/帮助文本），减少误配。

### 性能/可靠性
- 性能：
  - 鉴权逻辑 O(1)，不引入额外 I/O。
  - debug 日志脱敏是字典遍历 O(n)，仅在 debug 时生效，风险可控。
- 可靠性：
  - `backend/Dockerfile` 使用 `uv sync --frozen` 具备可重复性。
  - compose 增加 healthcheck，有助于服务编排可靠性。

### 安全/隐私
- 权限判定：
  - `/admin/v1/*` 与 `/{path:path}` 按需求受保护；`/health` 免鉴权。
- 敏感信息：
  - debug 日志对 `authorization/x-goog-api-key/x-ccg-token/cookie` 等做 mask。
- 透传风险：
  - 转发 header 过滤加入 `x-ccg-token`，避免客户端网关 token 向上游泄露。

### 测试/质量
- 单元测试：
  - `backend/tests/test_token_auth.py` 覆盖缺失/错误/正确 token 与关闭鉴权放行。
  - `backend/tests/test_redaction.py` 覆盖敏感 header 脱敏。
  - `backend/tests/test_forward_header_filter.py` 覆盖不透传规则。
- 集成测试：
  - `backend/tests/test_auth_integration.py` 采用最小 FastAPI app 验证“路由挂载依赖”语义，避免依赖真实 DB。
- 风险：
  - 测试对真实 app.main 的覆盖不足（见阻塞项 2）。

### 可维护性/文档
- 文档：
  - `DEPLOYMENT.md` 覆盖环境要求、配置、启动、升级、备份恢复、安全建议，并给出 curl 验收。
  - `SMOKE_TEST.md` 给出可复用清单，覆盖 /health、鉴权、持久化。
- 可维护性：
  - 目前鉴权配置在 `Settings` 中集中；但存在默认值与文档/行为不完全一致的风险（见阻塞项 1）。

### 学习/改进
- 可复用模式：
  - Router 级别 `dependencies=[Depends(...)]` 方式可推广到后续新增路由。
  - header 脱敏抽为纯函数，便于复用。
- 需记录的反模式：
  - 通过 `pytest_configure` 改写环境变量来绕过 Fail Fast，会导致“真实启动路径”未覆盖；建议后续抽离 settings 构建逻辑，便于测试。

## 详细问题

1. [阻塞] `GATEWAY_HOST` 默认值变更可能破坏桌面/本地默认绑定行为
   - 影响：桌面/本地运行默认从 `127.0.0.1` 变为 `0.0.0.0`，可能扩大暴露面；与原有“本机默认更安全”的预期冲突。
   - 证据：`backend/app/core/config.py` 曾将 `GATEWAY_HOST` 默认改为 `0.0.0.0`。
   - 建议：恢复默认 `127.0.0.1`，仅在 Docker/生产部署通过 env 覆盖为 `0.0.0.0`（Dockerfile/compose 已在 env 层具备覆盖能力）。
   - 优先级：P0
   - 状态：已解决

2. [阻塞] 真实应用路由集成测试缺失，可能遗漏启动期/依赖注入边界
   - 影响：当前“集成测试”验证的是最小 FastAPI app 的 dependency 行为，不保证 `app.main` 真实路由树中无遗漏（例如未来新增路由未挂依赖）。
   - 证据：此前仅有 `backend/tests/test_auth_integration.py`（最小 app），未覆盖 `app.main:app`。
   - 修复：新增 `backend/tests/test_auth_integration_app_main.py` 覆盖 `/health` 以及缺 token 时 admin/proxy 不会成功。
   - 优先级：P0
   - 状态：已解决

3. [建议] `docker-compose.yml` 对 `CCG_AUTH_TOKEN` 的“必填”缺少显式失败提示
   - 影响：compose 里 `CCG_AUTH_TOKEN: "${CCG_AUTH_TOKEN:-}"` 可能导致用户忘记设置而启动失败，但错误定位依赖日志。
   - 建议：在 `DEPLOYMENT.md` 增加“必须创建 .env 并设置 token”的首屏提示；或在 compose 注释中更明确说明。
   - 优先级：P1
   - 状态：未解决

4. [建议] 前端 axios token 头名未与后端可配置项联动
   - 影响：若 `CCG_AUTH_HEADER_NAME` 被部署者修改，前端固定写入 `X-CCG-Token` 会导致 UI 无法访问。
   - 建议：短期：文档强调不要改 header name；长期：前端增加“header name”配置或通过后端 settings 下发。
   - 优先级：P2
   - 状态：未解决

## Final Checklist
- [x] 已逐项评估功能、架构、性能、安全、可维护性、测试与文档。
- [x] 所有阻塞问题均已记录并反馈，关键建议已说明优先级。
- [x] 验证结果明确记录（见 Review Summary）。
- [x] 评审摘要与评论结构化，便于作者快速行动。
