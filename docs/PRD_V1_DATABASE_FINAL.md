# Aquant PRD v1.0 Final Database

Active migration baseline:

- `alembic/versions/20260505_0001_prd_v1_baseline.py`
- Latest incremental migration: `alembic/versions/20260512_0008_simplify_limit_up_stock.py`

This is a development reset baseline. Rebuild local development databases from this migration.

## Active Tables

### Market Data

- `stock_basic`
- `mkt_daily`
- `mkt_hot_board`
- `mkt_hot_stock`
- `mkt_limit_up_stock`
- `mkt_limit_up_plate`
- `mkt_stock_kline_daily`
- `mkt_stock_kline_15m`

Market data tables retain source/platform traceability fields such as `source`, `platform`, `source_url`, `source_update_time`, and `collected_at` where applicable.
Limit-up ladder display is now calculated from `mkt_limit_up_stock.ladder_height` / `board_count`; no standalone ladder table is active.

### Watch, Signals, Trades

- `watch_pool`
- `watch_pool_status_log`
- `watch_signal`
- `watch_signal_performance`
- `watch_trade`
- `watch_trade_execution`

Watch-pool records are manually created. Trade records use `watch_trade` as the master table and `watch_trade_execution` as the buy/sell execution ledger.

### Reviews

- `review_form`
- `review_weekly`
- `review_monthly`
- `review_trade`

### My Module

- `my_user_profile`
- `my_user_preference`
- `my_notification_setting`

### Admin Configuration

- `config_data_source`
- `config_task`
- `config_task_log`
- `config_field_mapping`
- `config_dictionary`
- `config_strategy`
- `config_notification_template`
- `config_notification_record`
- `config_review_template`
- `config_operation_log`

## Key Unique Constraints

- `mkt_daily`: `trade_date + source`
- `mkt_hot_board`: `trade_date + platform + board_name`
- `mkt_hot_stock`: `trade_date + platform + stock_code`
- `mkt_limit_up_stock`: `trade_date + source + stock_code`
- `mkt_limit_up_plate`: `trade_date + source + plate_code`
- `mkt_stock_kline_daily`: `stock_code + trade_date + source`
- `mkt_stock_kline_15m`: `stock_code + kline_time + source`
- `watch_signal`: `stock_code + buy_point_type + signal_type + trigger_date`
- `watch_signal_performance`: `signal_id`
- `review_form`: `review_type + review_period`
- `config_notification_record`: `push_type + target_type + target_id + channel`

## Removed From Active Schema

The following old MVP/v1.1 tables are no longer active PRD v1 models:

- `market_daily`
- `sector_daily`
- `hot_stock_rank`
- `limit_up_daily`
- `stock_kline_daily`
- `stock_kline_15m`
- `signal_record`
- `trade_record`
- `trade_review`
- `strategy_config`
- `system_task_log`
- `watch_pool_lifecycle`
- `watch_pool_score`
- `daily_trade_plan`
- `daily_trade_plan_item`
- `trade_execution_checklist`
- `sell_plan`
- `trade_error_tag`
- `trade_review_detail`
- `weekly_review`
- `monthly_review`
- `discipline_rule`
- `user_trading_score`
- `mkt_limit_up_ladder`
- `mkt_limit_up_ladder_stock`

Old migration files were archived to `alembic/archive_old/`.

## Local Rebuild

```powershell
$env:DATABASE_URL='sqlite:///./aquant_prd_v1.db'
$env:CANDLE_DATABASE_URL='sqlite:///./aquant_candle_prd_v1.db'
python -m alembic upgrade head
```

Seed defaults are initialized by common/admin/H5 endpoints that call `SeedService.init_defaults()`. For command-line validation, run:

```powershell
python -c "from app.core.database import SystemSessionLocal; from app.services.prd_v1 import SeedService; db=SystemSessionLocal(); print(SeedService(db).init_defaults()); db.close()"
```
