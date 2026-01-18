# 部署文档（Docker Compose）

本文档面向运维/部署人员，目标是在公网或内网环境中以 Docker Compose 一键部署 `ccg-gateway`，并满足安全与可维护性要求。

## 环境要求

- Windows / Linux / macOS 任一（本文示例以 Windows PowerShell 为主）
- Docker Desktop 或 Docker Engine
- Docker Compose（`docker compose`）

## 重要安全建议（必读）

- **必须开启鉴权**：默认 `CCG_AUTH_ENABLED=1`。
- **必须设置强随机 Token**：公网部署如果未设置 `CCG_AUTH_TOKEN`，后端会直接启动失败（Fail Fast）。
- 不建议直接把 `7788` 暴露到公网（如确需暴露，建议配合防火墙/访问控制/限流）。
- 建议通过 Nginx 容器统一对外提供 Web UI，并在外层再加 HTTPS（如 Caddy / Nginx / 云负载均衡）。
- 建议定期轮换 Token。

## 配置项

建议在仓库根目录创建 `.env`（与 `docker-compose.yml` 同级）。

必填：

```dotenv
# 网关鉴权（默认开启）
CCG_AUTH_ENABLED=1

# 必填：共享 Token
CCG_AUTH_TOKEN=please-change-to-a-strong-random-token

# 可选：自定义鉴权头名
CCG_AUTH_HEADER_NAME=X-CCG-Token
```

可选（有默认值）：

- `GATEWAY_PORT`：容器内监听端口，默认 `7788`
- `LOG_TO_FILE`：是否写入 `data/app.log`，默认关闭；compose 默认开启

## 启动

在仓库根目录执行：

```powershell
docker compose up -d --build
```

检查服务：

```powershell
docker compose ps
```

默认访问：

- Web UI：`http://127.0.0.1/`
- 健康检查：`http://127.0.0.1/health`

## 验收（curl）

1) 健康检查无需 Token：

```bash
curl -i http://127.0.0.1/health
```

2) 未带 Token 访问管理 API 应返回 401：

```bash
curl -i http://127.0.0.1/admin/v1/settings
```

3) 带 Token 访问管理 API：

```bash
curl -i \
  -H "X-CCG-Token: $CCG_AUTH_TOKEN" \
  http://127.0.0.1/admin/v1/settings
```

## 数据持久化

compose 默认把宿主机 `./data` 挂载到容器 `/app/data`，用于持久化：

- `data/ccg_gateway.db`
- `data/backups/*`
- `data/app.log`（启用日志落盘时）

## 升级

1) 拉取新版本代码
2) 重新构建并重启：

```powershell
docker compose pull --ignore-pull-failures
docker compose up -d --build
```

## 备份与恢复

最简单方式：直接备份 `data/` 目录。

- 备份：复制 `data/ccg_gateway.db`（以及 `data/backups/`）
- 恢复：停止服务后替换 `data/ccg_gateway.db`，再启动

```powershell
docker compose down
# 还原 data/ccg_gateway.db
docker compose up -d
```

