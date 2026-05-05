# Final PRD v1 Gap Fix Log

## 2026-05-05

### 已修复

- 从正式 API 路由中移除 `/api/v1/**` 注册，旧 v1.1 能力不再进入 PRD v1 主流程。
- 新增 `/api/h5/watch-signals/**`：信号列表、最近信号、详情、忽略、误报、失效、表现、确认买入。
- 新增 `/api/h5/watch-trades/**`：交易列表、最近交易、详情、执行流水、确认卖出、取消、关闭、更新、汇总。
- 新增 `/api/h5/reviews/**`：周复盘、月复盘、单笔交易复盘、待办、保存、完成、归档。
- 确认买入改为写入 `watch_trade + watch_trade_execution`，并对同一信号重复确认做幂等处理。
- 确认卖出改为写入 `watch_trade_execution`，支持部分卖出和全部卖出；全部卖出后生成 `review_trade`。
- H5 `/watch-pool` 对齐为“观察 / 信号 / 交易”三个二级 Tab，调用 `/api/h5/**` PRD 接口。
- H5 `/reviews` 对齐为“周复盘 / 月复盘”两个二级 Tab，移除旧每日计划入口。
- H5 旧 `/daily-plan`、`/signals`、`/trades`、`/sectors`、`/monthly-review` 路由已重定向，不进入主导航。
- 增加 PRD v1 接口测试，覆盖确认买入、买入流水、重复确认买入、确认卖出、交易完成生成单笔复盘、复盘查询。

### 已验证

- `python -m compileall app`：通过。
- `python -m pytest tests/test_prd_v1_api.py -q`：6 passed。
- `python -m pytest -q`：30 passed。
- `npm run test`：1 passed。
- `npm run build`：通过。
- Alembic 干净 SQLite 迁移验证：通过。

### 仍为 partial

- 策略引擎生成链路仍有一部分旧 `signal_record` 兼容代码，最终应统一写入 `watch_signal`。
- 旧 `trade_record` 服务仍保留用于历史兼容，H5 新主流程已使用 `watch_trade`。
- 周/月复盘定时生成任务还需要继续接入 `config_task`。
- 后台管理页面仍未完整实现；当前具备后台 API 和 H5 我的页后台入口。
