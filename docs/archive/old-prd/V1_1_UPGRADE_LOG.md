# Aquant v1.1 增量升级日志

## Phase 0：v1.0 现状审计与 v1.1 升级计划

- 已扫描后端、前端、迁移、测试、Docker 和文档结构。
- 已确认 v1.0 核心能力基本存在：market、sector、hot stock、limit up、watch pool、kline、indicator、signal engine、trade、review、task log、H5 核心页面。
- 已找到 `Aquant需求文档_v1.0.md`。
- 未在当前工作区找到 `Aquant需求文档_v1.1.md`，本轮按用户消息中的 v1.1 需求执行。
- 已创建 v1.1 升级计划、验收、合规和 API 文档占位。

## 执行原则

- 本次是 v1.1 增量升级，不是 v1.0 重做。
- 不删除旧表字段，不重命名旧 API，不破坏旧路由。
- 无法完整实现的 P1/P2 能力将记录降级范围，并优先保证 P0 后端闭环可测试。

## Phase 1：数据库增量迁移

- 已新增 v1.1 模型：生命周期、评分、每日计划、检查清单、卖出计划、错误标签、单笔复盘、周/月复盘、纪律规则、能力评分、站内通知。
- 已增量扩展 `watch_pool`、`trade_record`、`signal_record` 模型字段。
- 已新增 Alembic 迁移 `20260430_0002_v1_1_incremental.py`，采用安全检查后创建表和添加字段。

## Phase 2-16：后端 v1.1 核心闭环

- 已实现 `app/services/v1_1.py`，覆盖自选生命周期、Watch Score、自动归档、纪律规则、严格模式、每日计划、买入前检查、计划外交易、卖出计划、单笔复盘、错误标签、周/月复盘、通知和 v1.1 任务入口。
- 已新增 `/api/v1/...` API 路由，不替换 v1.0 API。
- 已更新兼容版 `TradeService.confirm_trade` 和 `sell_trade`，写入计划关联、计划外标记和部分卖出状态。
- 降级说明：站外推送、真实公告风险、真实竞价刷新、实际 K 线图上买卖点绘制暂以 mock/站内记录和摘要数据实现。

## Phase 17-21：H5 增量页面

- 已新增 `/daily-plan` 今日计划页。
- 已新增 `/monthly-review` 月度总结页。
- 已新增 `/trades/:tradeId/review` 单笔复盘页。
- 已更新底部导航，增加计划入口。
- `/watch-pool` 细粒度筛选和完整时间线弹层仍为后续增强项，后端 API 已具备基础。

## Phase 22-24：文档、测试与合规

- 已更新 v1.1 API、验收、合规文档。
- 已新增 `tests/test_v1_1_flow.py`，覆盖核心闭环。
- Alembic 本地 SQLite 迁移验证：`alembic upgrade head` 成功。
- 后端测试：`21 passed`。
- 前端构建：`vite build` 成功。
- 前端测试：`1 passed`。
- 合规关键词扫描范围 `app frontend/src docs tests` 无命中。

## 2026-05-01：每日真实数据采集

- 已接入 APScheduler 每日一次 `generate_daily_snapshot_task` 调度。
- 默认 `ENABLE_SCHEDULER=false`，避免开发环境启动后立即采集；需要每日采集时显式开启。
- 新增 `DAILY_COLLECTION_HOUR`、`DAILY_COLLECTION_MINUTE`、`TIMEZONE` 配置。
- 管理任务接口支持 `trade_date=YYYY-MM-DD` 参数，可补采指定日期。
