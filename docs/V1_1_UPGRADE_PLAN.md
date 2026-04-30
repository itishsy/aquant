# Aquant v1.1 增量升级计划

## 基线说明

本次升级基于 v1.0 既有实现做增量扩展，不重做 v1.0，不删除旧表字段，不重命名既有 API 和 H5 路由。仓库中已找到 `Aquant需求文档_v1.0.md`；未在当前工作区找到 `Aquant需求文档_v1.1.md` 文件，本计划以用户本轮提供的 v1.1 需求文本为执行依据。

## v1.0 已有能力

- Backend：FastAPI、SQLAlchemy、Alembic、Provider 抽象、mock/real provider、任务日志。
- Services：market、sector、hot stock、limit up、watch pool、kline、indicator、signal engine、trade、review、tasks。
- API：health、market、sectors、hot-stocks、limit-up、watch-pool、stocks、signals、trades、reviews、admin。
- Frontend：React/Vite H5，已有 market、sectors、watch-pool、stock detail、signals、trades、reviews、settings 页面。
- Tests：pytest 后端测试与前端 vitest/build。
- Docker：已有本地开发配置。

## v1.1 增量目标

将 Aquant 从行情监测和基础复盘升级为个人短线交易训练系统，补齐自选股生命周期、Watch Score、每日交易计划、买入前检查、计划外交易识别、卖出计划、单笔复盘、错误标签、周/月复盘增强、严格模式、站内提醒和 v1.1 任务入口。

## 数据库方案

新增 v1.1 表：`watch_pool_lifecycle`、`watch_pool_score`、`daily_trade_plan`、`daily_trade_plan_item`、`trade_execution_checklist`、`sell_plan`、`trade_error_tag`、`trade_review_detail`、`weekly_review`、`monthly_review`、`discipline_rule`、`user_trading_score`、`notification_record`。

增量扩展旧表：`watch_pool`、`trade_record`、`signal_record`。新增字段全部 nullable 或有默认值，避免破坏旧数据。

## 服务升级方案

- Watch：生命周期、评分、分层、归档、黑名单保护。
- Plan：每日交易计划生成、计划项触发/失效/完成。
- Discipline：纪律规则和严格模式。
- Trade：买入前检查、计划外交易、卖出计划、单笔复盘。
- Review：v1.1 周复盘、月度总结、交易能力评分。
- Notification：站内/mock 提醒记录。
- Tasks：v1.1 手动任务入口，失败写 `system_task_log`。

## API 升级方案

保留 v1.0 API，新增 `/api/v1/...` 路由，包括自选生命周期、评分、纪律规则、严格模式、每日计划、检查清单、计划外交易、卖出计划、复盘详情、错误标签、周/月复盘、通知和后台任务。

## H5 升级方案

保留既有路由，增量增强 `/watch-pool`、`/reviews`，新增 `/daily-plan`、`/monthly-review`、`/trades/:tradeId/review`。所有交易确认入口必须先进入检查清单或展示检查清单弹层，不提供任何自动化委托或快捷委托入口。

## 测试策略

新增 v1.1 闭环测试，覆盖生命周期、评分、每日计划、检查清单、严格模式、计划外交易、卖出计划、单笔复盘、错误标签、周/月复盘、通知。保留 v1.0 回归测试，前端执行 build 和 vitest。

## 合规边界

系统只做行情监测、辅助分析、信号提醒、人工确认、交易记录、复盘训练。禁止自动下单、券商接口、收益承诺和诱导性买卖文案。所有信号、计划、提醒和复盘均体现“仅作为交易辅助，请结合个人交易计划确认。”
