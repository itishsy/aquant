# Aquant PRD v1.0 对齐审计

审计日期：2026-05-05  
基准文档：`Aquant PRD v1.0.md`（单用户开发就绪版）  
审计范围：后端、前端、数据库迁移、测试、Docker、文档。  
审计约束：本次仅审计与产出文档，不修改业务代码、数据库或前端页面。

## 1. 当前项目结构

```text
aquant/
  app/                    FastAPI 后端
    api/routes/            现有 API 路由
    core/                  配置、数据库连接
    models/                SQLAlchemy 模型
    providers/             mock/real provider
    services/              市场、自选、信号、交易、复盘、任务等服务
    strategies/            MACD15、风险策略
    tasks/                 APScheduler 入口
  alembic/                 数据库迁移
  frontend/                React + Vite + Ant Design Mobile H5
  tests/                   pytest 后端测试 + vitest 前端测试
  docs/                    历史实现文档、API、验收、v1.1 文档
  docker-compose.yml       backend/frontend/redis 本地编排
  Dockerfile.backend
  Dockerfile.frontend
  requirements.txt
```

## 2. 当前实现现状

后端现状：

- 已有 FastAPI 应用入口、统一 `/api` 前缀、健康检查。
- 已有系统库与 K 线库双库连接：`DATABASE_URL`、`CANDLE_DATABASE_URL`。
- 已有 Provider 抽象：`base.py`、`mock_provider.py`、`real_provider.py`、`factory.py`。
- 已有服务：市场、板块、热股、涨停、K 线、指标、数据质量、信号引擎、交易、复盘、任务、自选池。
- 已有 v1.1 风格服务集中在 `app/services/v1_1.py`，包含 Watch Score、每日计划、严格模式、检查清单、卖出计划、复盘增强、通知等。
- 已有后台任务路由 `/api/admin/tasks/**`，采用 `X-Admin-Token` 简单校验。

前端现状：

- 已有 H5 页面：`/market`、`/sectors`、`/watch-pool`、`/stocks/:stockCode`、`/signals`、`/daily-plan`、`/trades`、`/reviews`、`/monthly-review`、`/settings`。
- 底部导航当前为：市场、计划、自选、复盘、设置。
- 个股详情页在 H5 中直接绘制日 K 和 15 分钟线图。
- 市场页已具备日期切换、大盘/热榜/涨停榜 Tab。

数据库与迁移现状：

- Alembic 有两版迁移：`20260426_0001_init_mvp.py`、`20260430_0002_v1_1_incremental.py`。
- 当前模型包含早期 MVP 表、K 线表和大量 v1.1 增量表。
- 当前表名以 `market_daily`、`sector_daily`、`hot_stock_rank`、`limit_up_daily`、`signal_record`、`trade_record`、`trade_review` 等为主。
- 最新 PRD 要求表名和领域边界主要为 `mkt_*`、`watch_*`、`review_*`、`my_*`、`config_*`。

测试现状：

- 后端测试覆盖 API、市场评分、热门股、数据质量、标准化、信号引擎、交易复盘、自选池、v1.1 流程。
- 现有测试明显绑定旧实现，例如 Market Score、自动入池、Watch Score、v1.1 严格模式。
- 前端有 `src/api/client.test.ts` 基础测试。

Docker 现状：

- `docker-compose.yml` 包含 backend、frontend、redis。
- 未包含 MySQL 服务，当前默认连接远程 MySQL。
- backend Docker 环境变量中 `DATA_PROVIDER_MODE=mock`，代码默认配置中 `data_provider_mode=real`，存在环境差异。

文档现状：

- 存在旧版 `AI_IMPLEMENTATION_*`、`MVP_ACCEPTANCE.md`、`API.md`、`V1_1_*`、`REAL_DATA_COLLECTION.md`。
- 这些文档大量描述旧 MVP/v1.1 能力，部分内容与最新 PRD v1.0 已冲突。

## 3. 与最新 PRD 一致的模块

可以保留并作为迁移基础：

- FastAPI + SQLAlchemy + Alembic 技术栈：符合 PRD 建议的 Python FastAPI / MySQL / APScheduler 方向。
- Provider 抽象：PRD 要求数据源、字段映射、采集任务可后台管理，现有 provider 层可复用为采集适配基础。
- 真实数据采集雏形：`real_provider.py` 和市场复盘采集可作为 `mkt_*` 数据采集的原型，但需要治理授权、字段映射和任务日志。
- 数据标准化与质量校验：`normalization.py`、`quality.py` 可复用。
- K 线后台计算能力：`kline.py`、`indicator.py`、策略中使用 K 线的能力符合“后台计算，不在前台展示 K 线”的方向。
- 信号策略框架：`strategies/base.py`、`macd15.py`、`risk.py` 可保留为策略计算内核。
- 人工确认交易原则：现有交易服务未发现自动下单、券商接口或一键下单，可继续保留合规边界。
- 任务日志基础：`system_task_log` 和任务服务可迁移到 PRD 的 `config_task_log`。
- H5 移动端基础：React/Vite/Ant Design Mobile、底部 Tab、卡片式页面可复用。

## 4. 与最新 PRD 冲突的模块

### 4.1 自动入池冲突

最新 PRD 明确要求“全部自选股均由用户手动入选”，市场页只提供“添加自选”入口，不自动加入自选池。

当前冲突点：

- `WatchPoolService.auto_add_candidates()` 会根据热门股和主线板块自动入池。
- `TaskService.auto_update_watch_pool_task()` 会触发自动更新自选池。
- 旧验收文档和测试中存在“自动入池有评分、原因、分层”等 v1.1 目标。

结论：需要停用自动入池任务和服务入口，保留手动添加逻辑并改造成 PRD 的添加自选弹框流程。

### 4.2 主观评分冲突

最新 PRD 市场数据模块只展示客观原始数据：

- 不自建 Market Score。
- 不自建 Sector Score。
- 热门个股只展示平台原始排名和原始分数，不做综合加分、扣分或主观排序。

当前冲突点：

- `MarketDaily.market_score`、`MarketService.calculate_market_score()`。
- `SectorDaily.sector_score`、`SectorService.calculate_sector_score()`。
- `WatchPoolScore`、`WatchScoreService`。
- `HotStockRank.rank_score/resonance_score/total_score` 和热股综合评分。
- 前端 `MarketPage` 展示市场温度；`SectorsPage` 展示板块评分；`DailyPlanPage` 使用 market_score / sector_score。

结论：评分逻辑应停用或降级为内部实验字段，不应作为最新 PRD v1.0 的 H5 展示与主排序依据。市场模块应回归 `mkt_*` 原始字段。

### 4.3 H5 K 线图冲突

最新 PRD 明确：K 线仅用于后台策略计算、买点扫描和复盘统计，系统内不展示 K 线图，用户查看 K 线统一跳转雪球。

当前冲突点：

- `StockDetailPage.tsx` 调用 `/stocks/{stock_code}/kline/daily`、`/stocks/{stock_code}/kline/15m`。
- `StockDetailPage.tsx` 使用 `LineChart` 和 `MiniBars` 展示日 K、15 分钟 MACD。
- `frontend/src/components/LineChart.tsx` 是为前台图表展示服务。

结论：H5 个股详情页需改造为基础信息、来源摘要、历史信号、交易记录、复盘记录、雪球链接，不展示 K 线图。K 线 API 可保留为后台/策略接口，不作为 H5 页面接口。

### 4.4 交易记录模型冲突

最新 PRD 要求：

- `watch_trade` 记录完整交易生命周期。
- `watch_trade_execution` 记录每次买入、卖出、减仓、清仓流水。

当前冲突点：

- 现有为 `trade_record` 单表承载买入和卖出字段。
- 现有 `sell_plan` 是 v1.1 风格计划表，不等同于执行流水。
- 缺失 `watch_trade_execution`。

结论：交易模块需要迁移到主表 + 执行流水模型。`trade_record` 可作为旧数据迁移来源，不建议继续扩展。

### 4.5 API 前缀冲突

最新 PRD 规定：

- H5 前台：`/api/h5/**`
- 后台管理：`/api/admin/**`
- 公共接口：`/api/common/**`

当前冲突点：

- 现有 H5 业务 API 多为 `/api/market/**`、`/api/watch-pool`、`/api/signals`、`/api/trades`、`/api/reviews`、`/api/stocks/**`。
- v1.1 API 为 `/api/v1/**`，最新 PRD 不采用该分层。
- 后台管理仅有 `/api/admin/tasks/**`，覆盖不足。
- 缺失 `/api/common/auth/**`、`/api/common/dictionaries`、`/api/h5/me/**` 等。

结论：需要新增 PRD 版 API 层，旧 API 暂做兼容或内部调用，最终 H5 切换到 `/api/h5/**`。

### 4.6 v1.1 过度功能冲突

当前存在一批最新 PRD v1.0 未要求或边界不同的 v1.1 功能：

- `daily_trade_plan`、`daily_trade_plan_item`
- `trade_execution_checklist`
- `watch_pool_score`
- `discipline_rule`
- `user_trading_score`
- `strict_mode`
- `/daily-plan`、`/monthly-review`、`/api/v1/**`

结论：这些功能不是最新 PRD v1.0 的 P0 主线，应停用前台入口或标记为实验，避免干扰“单用户开发就绪版”的核心闭环。

### 4.7 后台管理系统缺口

最新 PRD 要求后台管理系统包含：

- 工作台
- 数据源管理
- 采集任务管理
- 字段映射
- 策略管理
- 字典管理
- 复盘模板
- 消息推送模板
- 日志中心
- 账号与安全

当前现状：

- 后端只有 `/api/admin/tasks/logs` 与 `/api/admin/tasks/{task_name}/run`。
- 没有后台 Web 页面。
- 没有 `config_data_source`、`config_task`、`config_field_mapping`、`config_dictionary`、`config_strategy`、`config_notification_template`、`config_review_template`、`config_operation_log` 等表。

结论：后台管理系统需要新增，是当前最大 P0 缺口之一。

### 4.8 我的模块缺口

最新 PRD 要求“我的”模块，包含个人资料、消息偏好、待办提醒、系统状态摘要、后台入口。

当前现状：

- 前端为 `/settings`，不是 `/me` 或“我的”模块。
- 后端没有 `my_user_profile`、`my_user_preference`、`my_notification_setting`。
- 缺失 `/api/h5/me/**`。

结论：需要新增或将 `/settings` 改造为“我的”模块。

## 5. 可复用代码

建议保留：

- `app/core/config.py`、`app/core/database.py`：保留双库能力，但敏感配置应外置。
- `app/providers/base.py`、`mock_provider.py`、`real_provider.py`、`factory.py`：改造成后台数据源配置驱动。
- `app/services/normalization.py`、`quality.py`：继续作为数据治理基础。
- `app/services/kline.py`、`indicator.py`：保留为后台计算服务，移出 H5 直连展示。
- `app/strategies/base.py`、`macd15.py`、`risk.py`：保留为策略引擎核心。
- `app/services/signal_engine.py`：保留扫描自选池和保存 raw snapshot 的方向，但需改用 `watch_signal`。
- `app/services/tasks.py`：保留任务日志包装与手动触发机制，迁移到 `config_task/config_task_log`。
- `frontend/src/components/PageShell.tsx`、`BottomTabs.tsx`、`StockLink.tsx`、基础样式：可复用移动端视觉基础。
- Dockerfile、requirements、Alembic 基础结构：可复用。

## 6. 建议停用或废弃代码

建议停用：

- 自动入池：`WatchPoolService.auto_add_candidates()`、`TaskService.auto_update_watch_pool_task()`、相关测试。
- 主观评分展示：Market Score、Sector Score、Watch Score 的前台展示与排序。
- v1.1 每日计划/严格模式/检查清单/能力评分相关前台入口与 API：先标记实验，不纳入最新 v1.0 主线。
- H5 K 线图：`StockDetailPage` 中的 `LineChart`、`MiniBars` K 线展示。
- `/api/v1/**`：不应作为最新 v1.0 正式 API，对外文档应改为 `/api/h5/**`、`/api/admin/**`、`/api/common/**`。
- 旧文档中的 `V1_1_*` 验收目标：与最新 PRD v1.0 冲突，应归档，不作为当前验收标准。

建议重写或重建：

- 交易记录数据模型：由 `trade_record` 重建为 `watch_trade` + `watch_trade_execution`。
- 复盘模型：由 `trade_review`、`weekly_review`、`monthly_review` 重建或映射到 `review_form`、`review_weekly`、`review_monthly`、`review_trade`。
- 后台配置模型：新增 `config_*` 表族。
- 我的模块模型：新增 `my_*` 表族。

## 7. 数据库差异

当前表：

- 市场：`market_daily`、`market_review_daily`、`sector_daily`、`hot_stock_rank`、`limit_up_daily`
- K 线：`stock_kline_daily`、`stock_kline_15m`
- 自选/信号/交易：`watch_pool`、`signal_record`、`trade_record`、`trade_review`
- 任务：`system_task_log`
- v1.1：`watch_pool_lifecycle`、`watch_pool_score`、`daily_trade_plan`、`daily_trade_plan_item`、`trade_execution_checklist`、`sell_plan`、`trade_error_tag`、`trade_review_detail`、`weekly_review`、`monthly_review`、`discipline_rule`、`user_trading_score`、`notification_record`

最新 PRD 要求的核心表：

- 市场：`mkt_daily`、`mkt_hot_board`、`mkt_hot_stock`、`mkt_limit_up`、`mkt_stock_kline_daily`、`mkt_stock_kline_15m`
- 自选：`watch_pool`、`watch_signal`、`watch_signal_performance`、`watch_pool_status_log`、`watch_trade`、`watch_trade_execution`
- 复盘：`review_form`、`review_weekly`、`review_monthly`、`review_trade`
- 我的：`my_user_profile`、`my_user_preference`、`my_notification_setting`
- 后台：`config_data_source`、`config_task`、`config_task_log`、`config_field_mapping`、`config_dictionary`、`config_strategy`、`config_notification_template`、`config_notification_record`、`config_review_template`、`config_operation_log`

主要差异：

- 市场表命名和字段不一致，且当前包含主观评分字段。
- 热门板块当前为 `sector_daily`，PRD 要求 `mkt_hot_board` 保留平台、排名、原始热度字段。
- 热门个股当前做综合评分，PRD 要求保存平台原始排名/分数。
- 涨停表当前缺少标准 `platform/source_url/source_update_time/collected_at` 等字段。
- K 线表当前在 `a_candle` 库中，但命名、字段如 `open/high/low/close` 与 PRD 的 `open_price/high_price/...` 不完全一致。
- 自选表缺少 PRD 的 `watch_id`、`pool_status`、`monitor_enabled`、`operation_strategies`、`buy_point_types`、`source_*` 等字段。
- 信号表当前为 `signal_record`，缺少 `watch_signal_performance`。
- 交易缺少执行流水表。
- 复盘缺少统一 `review_form`。
- 我的模块和后台配置表族基本缺失。

## 8. API 差异

当前 API：

- `/api/health`
- `/api/market/daily`、`/api/market/summary`、`/api/market/review`
- `/api/sectors/top`
- `/api/hot-stocks/top`
- `/api/limit-up/list`、`/api/limit-up/summary`
- `/api/watch-pool`
- `/api/stocks/{stock_code}/kline/daily`、`/api/stocks/{stock_code}/kline/15m`
- `/api/signals`
- `/api/trades`
- `/api/reviews`
- `/api/admin/tasks/**`
- `/api/v1/**`

最新 PRD API：

- `/api/common/**`
- `/api/h5/market/**`
- `/api/h5/watch-pool/**`
- `/api/h5/watch-signals/**`
- `/api/h5/watch-trades/**`
- `/api/h5/reviews/**`
- `/api/h5/me/**`
- `/api/h5/notifications/**`
- `/api/admin/**`

主要差异：

- 缺少统一登录/当前用户/字典/股票简要信息公共接口。
- H5 API 前缀不一致。
- 缺少 `/api/h5/market/trading-dates`、`hot-boards`、`hot-stocks`、`limit-ups` 等 PRD 标准接口。
- 缺少按 `watch_id` 操作的自选接口。
- 缺少 `watch-signals`、`watch-trades` 命名体系。
- 缺少 `watch_trade_execution` 查询和确认卖出接口。
- 缺少“我的”与通知接口。
- 后台管理 API 覆盖非常不足。

## 9. H5 页面差异

当前页面：

- `/market`
- `/sectors`
- `/watch-pool`
- `/stocks/:stockCode`
- `/signals`
- `/daily-plan`
- `/trades`
- `/trades/:tradeId/review`
- `/reviews`
- `/monthly-review`
- `/settings`

最新 PRD 页面主结构：

- 市场
- 自选
- 复盘
- 我的
- 后台管理系统

主要差异：

- 当前多出 `/sectors`、`/daily-plan`、`/monthly-review` 作为独立入口，最新版 PRD 应收敛到市场/自选/复盘/我的主导航。
- 当前 `/settings` 应改造为“我的”。
- 当前个股详情页展示 K 线图，最新版要求跳转雪球查看 K 线。
- 市场页应展示原始榜单、平台排名、原始分数、涨停原因，并提供添加自选入口；不应展示主观评分。
- 自选页需要按 PRD 拆成观察区、信号区、交易区，围绕手动入选、买点监控、确认买入、交易展示。
- 复盘页需要以周/月/单笔交易复盘表单为主，而不是 v1.1 能力评分导向。
- 缺少后台管理 Web 页面。

## 10. 冲突点专项结论

| 检查项 | 当前状态 | PRD 要求 | 结论 |
| --- | --- | --- | --- |
| 自动入池 | 存在 `auto_add_candidates` 和自动任务 | 全部自选股由用户手动入选 | 冲突，停用 |
| Market Score | 存在并前台展示 | 市场模块只展示客观原始数据 | 冲突，停用展示 |
| Sector Score | 存在并前台展示 | 热门板块展示平台原始榜单 | 冲突，停用展示 |
| Watch Score | v1.1 已实现 | PRD v1.0 未要求，且自选手动入选 | 冲突，停用 |
| H5 K 线图 | 个股详情展示日 K/15m 图 | 前台不展示 K 线，跳雪球 | 冲突，改造 |
| 自动交易/下单 | 未发现券商接口/自动下单 | 禁止 | 基本一致 |
| 多用户复杂权限 | 未实现复杂多用户，只有 admin token | 单用户，登录 + 后台入口边界 | 方向一致但需补登录 |
| 交易模型 | `trade_record` 单表 | `watch_trade + watch_trade_execution` | 冲突，重建 |
| 我的模块 | 只有 `/settings` | 资料、偏好、通知、待办、后台入口 | 缺失，新增/改造 |
| 后台管理 | 只有任务 API | 完整后台管理系统 | 缺失，新增 |

## 11. 风险点

- 历史代码混合了 MVP 和 v1.1 目标，若直接继续开发会把“新版 v1.0”做成“旧 v1.1”，产品边界会继续漂移。
- 数据库表名差异较大，直接重命名风险高，建议新增 PRD 表并迁移数据。
- 当前 `config.py` 默认写有远程数据库连接，应迁移到 `.env`，避免敏感配置固化。
- 旧测试会因为停用 Market Score、Watch Score、自动入池而失败，需要同步重写测试基准。
- 前端多页面和底部导航需要收敛，否则用户路径会与 PRD 不一致。
- 真实数据源接入需要确认授权边界，后台数据源配置和字段映射应先建好再扩大采集。
