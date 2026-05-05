# Aquant PRD v1.0 数据库最终文档

状态：阶段性交付。已新增模型与 Alembic 迁移 `20260505_0003_prd_v1_alignment.py`。

原则：

- 新增 PRD 标准表，不删除旧表。
- 旧 MVP/v1.1 表保留为兼容和迁移来源。
- 系统数据使用 `a_quant`，K 线计算数据使用 `a_candle`。

目标表族：

- 市场：`mkt_daily`、`mkt_hot_board`、`mkt_hot_stock`、`mkt_limit_up`。
- K 线：`mkt_stock_kline_daily`、`mkt_stock_kline_15m`。
- 自选/信号/交易：`watch_pool`、`watch_signal`、`watch_signal_performance`、`watch_pool_status_log`、`watch_trade`、`watch_trade_execution`。
- 复盘：`review_form`、`review_weekly`、`review_monthly`、`review_trade`。
- 我的：`my_user_profile`、`my_user_preference`、`my_notification_setting`。
- 后台配置：`config_data_source`、`config_task`、`config_task_log`、`config_field_mapping`、`config_dictionary`、`config_strategy`、`config_notification_template`、`config_notification_record`、`config_review_template`、`config_operation_log`。

本文件会随迁移阶段持续更新。

## 已新增迁移

- `alembic/versions/20260505_0003_prd_v1_alignment.py`

## 唯一约束

- `mkt_daily`: `trade_date + source`
- `mkt_hot_board`: `trade_date + platform + board_name`
- `mkt_hot_stock`: `trade_date + platform + stock_code`
- `mkt_limit_up`: `trade_date + platform + stock_code`
- `mkt_stock_kline_daily`: `stock_code + trade_date + source`
- `mkt_stock_kline_15m`: `stock_code + kline_time + source`
- `watch_signal`: `stock_code + buy_point_type + signal_type + trigger_date`
- `watch_signal_performance`: `signal_id`
- `review_form`: `review_type + review_period`
- `config_notification_record`: `push_type + target_type + target_id + channel`

## 旧表兼容说明

- 旧 `market_daily`、`sector_daily`、`hot_stock_rank`、`limit_up_daily` 暂作为 legacy 数据来源，H5 PRD 接口缺少 `mkt_*` 数据时会兼容同步。
- 旧 `signal_record`、`trade_record`、`trade_review` 暂保留，后续逐步迁移到 `watch_signal`、`watch_trade`、`watch_trade_execution`、`review_form`。
- 旧 v1.1 表族保留但不作为最新 PRD v1 主线。
