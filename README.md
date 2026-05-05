# Aquant PRD v1.0

Aquant 是单用户 A 股交易辅助系统。当前代码正在从旧 MVP/v1.1 混合实现迁移到最新版 `Aquant PRD v1.0.md`（单用户开发就绪版）。

核心边界：

- 不自动下单、不接券商交易接口、不提供一键下单或跟单。
- 市场数据只展示客观原始字段，不展示主观 Market/Sector/Watch Score。
- 自选股全部由用户手动加入。
- H5 前台不展示个股 K 线图，查看 K 线统一跳转雪球。
- 所有信号、交易、复盘均仅作为交易辅助，请结合个人交易规则确认。

## Local Backend

1. 使用 Python 3.12 创建虚拟环境。
2. 安装依赖：`pip install -r requirements.txt`
3. 复制环境变量：`.env.example -> .env`
4. 执行迁移：`alembic upgrade head`
5. 启动后端：`uvicorn app.main:app --reload`

## MySQL Layout

- 系统库：`8.148.181.1:3306 / a_quant`
- K 线库：`8.148.181.1:3306 / a_candle`


当前实现已按双库拆分：

- `a_quant`：市场、板块、热门股、涨停、自选池、信号、交易、复盘、任务日志等系统表
- `a_candle`：`stock_kline_daily`、`stock_kline_15m`

## Database Migration

- 系统库迁移：`alembic upgrade head`
- K 线表由应用启动时自动在 `a_candle` 初始化
- PRD v1 新增表见 `docs/PRD_V1_DATABASE_FINAL.md`

## Seed Data

默认字典、任务、策略、通知模板、复盘模板会在访问 `/api/common/auth/login` 或 `/api/common/dictionaries` 时幂等初始化。

## Data

- 建议开发环境使用 `DATA_PROVIDER_MODE=mock`。
- 真实数据源需确认授权边界，禁止绕过平台反爬或高频抓取未授权数据。
- 市场数据 PRD 接口位于 `/api/h5/market/**`。

## Frontend

1. 进入 `frontend`
2. 安装依赖：`npm install`
3. 启动 H5：`npm run dev`

H5 一级导航：市场、自选、复盘、我的。

## Tests

- Backend: `pytest`
- Frontend: `npm run test`
- Frontend build: `npm run build`

## Docker

- 启动全部服务：`docker compose up --build`
- 当前 `docker-compose.yml` 仅保留 `backend / frontend / redis`，MySQL 使用你提供的外部地址 `8.148.181.1`

## Compliance

- 系统仅提供行情监测、辅助分析、信号提醒、人工确认、交易记录、复盘分析。
- 禁止自动下单、券商接口交易、收益承诺与强诱导文案。
- 所有信号均仅作为交易辅助，请结合个人交易规则确认。

## PRD v1 Docs

- `docs/PRD_V1_ALIGNMENT_AUDIT.md`
- `docs/PRD_V1_MIGRATION_PLAN.md`
- `docs/PRD_V1_IMPLEMENTATION_LOG.md`
- `docs/PRD_V1_ACCEPTANCE_CHECKLIST.md`
- `docs/PRD_V1_API_FINAL.md`
- `docs/PRD_V1_DATABASE_FINAL.md`
- `docs/PRD_V1_COMPLIANCE_CHECK.md`
