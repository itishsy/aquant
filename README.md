# Aquant MVP

## Local Backend

1. 使用 Python 3.12 创建虚拟环境。
2. 安装依赖：`pip install -r requirements.txt`
3. 复制环境变量：`.env.example -> .env`
4. 启动后端：`uvicorn app.main:app --reload`

## MySQL Layout

- 系统库：`8.148.181.1:3306 / a_quant`
- K 线库：`8.148.181.1:3306 / a_candle`
- 用户名：`aquant`
- 密码：`Hsy@841121`

当前实现已按双库拆分：

- `a_quant`：市场、板块、热门股、涨停、自选池、信号、交易、复盘、任务日志等系统表
- `a_candle`：`stock_kline_daily`、`stock_kline_15m`

## Database Migration

- 系统库迁移：`alembic upgrade head`
- K 线表由应用启动时自动在 `a_candle` 初始化

## Mock Data

- 当前默认 `DATA_PROVIDER_MODE=mock`
- 首次访问相关 API 会自动写入 mock 数据
- 也可调用管理任务接口手动触发采集与扫描

## Frontend

1. 进入 `frontend`
2. 安装依赖：`npm install`
3. 启动：`npm run dev`

## Tests

- Backend: `pytest`
- Frontend: `npm run test`

## Docker

- 启动全部服务：`docker compose up --build`
- 当前 `docker-compose.yml` 仅保留 `backend / frontend / redis`，MySQL 使用你提供的外部地址 `8.148.181.1`

## Compliance

- 系统仅提供行情监测、辅助分析、信号提醒、人工确认、交易记录、复盘分析。
- 禁止自动下单、券商接口交易、收益承诺与强诱导文案。
- 所有信号均仅作为交易辅助。
