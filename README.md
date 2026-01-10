# CCG Gateway

支持 ClaudeCode、Codex、Gemini 的网关转发项目。

## 功能特性

- **网关转发**：监听端口 7788，原样转发请求到真实服务商
- **两种路由模式**：
  - 可用性优先：按权重顺序选择，失败后自动切换
  - 负载均衡：按权重轮询，同一会话保持同一服务商
- **服务商管理**：支持多服务商配置、拖拽排序、权重设置
- **自动拉黑**：连续失败 N 次后自动拉黑 M 分钟
- **超时控制**：流式首字节超时、流式静默超时、非流式超时
- **模型转发**：ClaudeCode 专属，支持模型名称映射
- **MCP 管理**：统一管理，三端开关控制
- **全局提示词**：统一管理，三端开关控制
- **使用统计**：请求数、成功率、Token 用量统计

## 技术栈

- **后端**：Python + FastAPI + SQLite
- **前端**：Vue3 + Element Plus + Pinia

## 快速开始

### 一键启动

**Windows**：
```bash
# 双击 start.bat 或在命令行运行
start.bat

# 停止服务
stop.bat
```

**Linux/macOS**：
```bash
chmod +x start.sh stop.sh

# 启动
./start.sh

# 停止
./stop.sh
```

### 手动启动

#### 后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --host 127.0.0.1 --port 7788 --reload
```

### 前端

```bash
cd frontend

# 安装依赖
pnpm install

# 开发模式
pnpm dev

# 构建
pnpm build
```

## 使用方法

1. 启动后端服务（默认端口 7788）
2. 启动前端开发服务器（默认端口 3000）
3. 访问 http://localhost:3000 进入管理界面
4. 添加服务商配置
5. 将 CLI 的 API 地址设置为 `http://127.0.0.1:7788`

### ClaudeCode 配置示例

在 `~/.claude/settings.json` 中添加：

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:7788",
    "ANTHROPIC_AUTH_TOKEN": "your-gateway-token"
  }
}
```

## 项目结构

```
ccg-gateway/
├── backend/                 # 后端代码
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   ├── schemas/        # Pydantic 模型
│   │   └── services/       # 业务逻辑
│   ├── data/               # SQLite 数据库
│   └── requirements.txt
├── frontend/               # 前端代码
│   ├── src/
│   │   ├── api/           # API 接口
│   │   ├── components/    # 组件
│   │   ├── stores/        # Pinia 状态
│   │   ├── types/         # TypeScript 类型
│   │   └── views/         # 页面
│   └── package.json
└── README.md
```

## API 端点

### 代理转发
- `ANY /{path}` - 转发请求到上游服务商

### 管理接口
- `GET /admin/v1/providers` - 服务商列表
- `POST /admin/v1/providers` - 添加服务商
- `PUT /admin/v1/providers/{id}` - 更新服务商
- `DELETE /admin/v1/providers/{id}` - 删除服务商
- `POST /admin/v1/providers/reorder` - 排序服务商
- `GET /admin/v1/settings` - 获取配置
- `PUT /admin/v1/settings/gateway` - 更新网关配置
- `PUT /admin/v1/settings/timeouts` - 更新超时配置
- `PUT /admin/v1/settings/cli/{cli_type}` - 更新 CLI 配置
- `GET /admin/v1/mcp` - MCP 列表
- `GET /admin/v1/prompts` - 提示词列表
- `GET /admin/v1/stats/daily` - 每日统计
- `GET /admin/v1/stats/providers` - 服务商统计

## License

MIT
