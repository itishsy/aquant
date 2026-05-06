# Ubuntu 三端启动

脚本：

- `scripts/start_ubuntu.sh`
- `scripts/stop_ubuntu.sh`

## 启动

```bash
chmod +x scripts/start_ubuntu.sh scripts/stop_ubuntu.sh
./scripts/start_ubuntu.sh
```

脚本会自动执行：

- 如果 `.env` 不存在，从 `.env.example` 复制一份。
- 创建 `.venv`。
- 安装后端依赖：`pip install -r requirements.txt`。
- 安装前端依赖：`npm install`。
- 执行数据库迁移：`python -m alembic upgrade head`。
- 初始化 PRD v1 默认种子数据。
- 初始化开发用 Mock 数据。
- 启动后端。
- 启动前端，H5 和后台管理共用同一个 Vite 服务。

## 默认访问地址

- 后端 API：`http://<服务器IP>:8000/api`
- H5：`http://<服务器IP>:5173/market`
- 后台管理：`http://<服务器IP>:5173/admin`

后台管理系统不进入 H5 底部导航，`/admin` 是独立页面入口。

## 常用参数

```bash
AQUANT_PUBLIC_HOST=你的服务器IP ./scripts/start_ubuntu.sh
BACKEND_PORT=8000 FRONTEND_PORT=5173 ./scripts/start_ubuntu.sh
SKIP_INSTALL=1 ./scripts/start_ubuntu.sh
SKIP_MIGRATION=1 ./scripts/start_ubuntu.sh
SKIP_MOCK_DATA=1 ./scripts/start_ubuntu.sh
```

如果 `.env.example` 中的 `VITE_API_BASE_URL` 是 `127.0.0.1` 或 `localhost`，脚本会自动替换为 `http://<服务器IP>:<后端端口>/api`，方便从外部浏览器访问。

## 日志和 PID

- 后端日志：`logs/backend.log`
- 前端日志：`logs/frontend.log`
- 后端 PID：`.run/backend.pid`
- 前端 PID：`.run/frontend.pid`

## 停止

```bash
./scripts/stop_ubuntu.sh
```

## 合规边界

脚本只启动服务、执行迁移、初始化默认配置和开发 Mock 数据，不会启用自动入池、自动交易、券商接口、Market Score、Watch Score、今日计划或严格模式等旧能力。
