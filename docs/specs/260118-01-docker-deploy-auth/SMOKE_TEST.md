# 部署级冒烟测试清单

目标：在发版/部署后，用一套可复用的步骤快速确认关键链路可用。

## 0. 前置

- 已完成 `docker compose up -d --build`
- `.env` 已配置 `CCG_AUTH_TOKEN`（且 `CCG_AUTH_ENABLED=1`）

为方便命令复用，建议先设置环境变量：

```bash
export CCG_AUTH_TOKEN='your-token'
```

## 1. 基础存活

- 期望：容器均为 running/healthy

```bash
docker compose ps
```

## 2. /health 无需鉴权

- 期望：`200`

```bash
curl -i http://127.0.0.1/health
```

## 3. 管理 API 鉴权

### 3.1 不带 Token

- 期望：`401`

```bash
curl -i http://127.0.0.1/admin/v1/settings
```

### 3.2 带 Token

- 期望：不是 `401/403`

```bash
curl -i \
  -H "X-CCG-Token: $CCG_AUTH_TOKEN" \
  http://127.0.0.1/admin/v1/settings
```

## 4. 转发入口鉴权（/{path:path}）

选择任意一个会走转发的路径（示例用 `/v1/models`，实际取决于你的 CLI/Provider）。

### 4.1 不带 Token

- 期望：`401`

```bash
curl -i http://127.0.0.1/v1/models
```

### 4.2 带 Token

- 期望：请求进入网关逻辑（返回值取决于是否已配置 provider），但**不应**是 `401/403`

```bash
curl -i \
  -H "X-CCG-Token: $CCG_AUTH_TOKEN" \
  http://127.0.0.1/v1/models
```

## 5. 数据持久化验证

- 期望：宿主机存在 `data/ccg_gateway.db`，重启后仍存在

```bash
ls -la data
```

```bash
docker compose restart
docker compose ps
ls -la data
```

