# Aquant PRD v1.0 Final Database

Active migration baseline:

- `alembic/versions/20260505_0001_prd_v1_baseline.py`
- Latest incremental migration: `alembic/versions/20260516_0018_drop_deleted_market_tables.py`

This is a development reset baseline. Rebuild local development databases from this migration.

## Active Tables

### Market Data

- `stock_basic`
- `mkt_daily`
- `mkt_hot_stock`
- `mkt_daily_plate`
- `mkt_daily_plate_stock`
- `mkt_limit_up_stock`
- `mkt_stock_kline_daily`
- `mkt_stock_kline_15m`

Market data tables retain source/platform traceability fields such as `source`, `platform`, `source_url`, `source_update_time`, and `collected_at` where applicable.
Limit-up ladder display is now calculated from `mkt_limit_up_stock.ladder_height` / `board_count`; no standalone ladder table is active.

`mkt_daily_plate` / `mkt_daily_plate_stock` are the active structured tables for daily plate/theme data. They keep the existing table structure unchanged and use `plate_type` to distinguish source categories:

- `plate_type = chance`: data migrated/collected from CLS `today_chances`; `subject_name -> plate_name`, `subject_id -> plate_code`, and `article_title` is retained as the plate display name/reason.
- `plate_type = tuyere`: data from CLS `today_tuyeres`.
- `plate_type = limit_up`: plate-level data from CLS `up_down_analysis.plate_stock`; collection and migration first exclude plate names `ST股` / `其他` / `其它`, then keep the top 3 plates by related limit-up stock count, with `rank_no` rewritten as `1`, `2`, `3`; `description` stores the board reason from upstream `up_reason` or aggregated stock `limit_reason` / `reason_tags`.
- `plate_type = hot_board`: replacement storage for hot-board/sector ranking data after `mkt_hot_board` was removed.
- `mkt_daily_plate_stock`: related stocks for each daily plate/theme row.

Legacy tables may remain in existing databases for rollback and audit, but new collection and H5 market reads use `mkt_daily_plate` and `mkt_daily_plate_stock`.

### Watch, Signals, Trades

- `watch_pool`
- `watch_pool_status_log`
- `watch_signal`
- `watch_signal_performance`
- `watch_trade`
- `watch_trade_execution`

Watch-pool records are manually created. Trade records use `watch_trade` as the master table and `watch_trade_execution` as the buy/sell execution ledger.

`20260514_0009_watch_pool_lifecycle_upgrade.py` is a development reset migration for the watch-pool lifecycle upgrade. It clears existing business rows from `watch_pool`, `watch_pool_status_log`, `watch_signal`, `watch_signal_performance`, `watch_trade`, `watch_trade_execution`, and `review_trade`, then adds the lifecycle fields required by `docs/自选池管理开发文档.md`.

#### `watch_pool` lifecycle fields

- `entry_source`: manual / hot_stock / limit_up.
- `entry_reason`: user-confirmed reason for adding the stock to the watch pool.
- `trading_system`: platform_breakout / uptrend / relay.
- `system_recommendation`: system-proposed trading system before user confirmation.
- `lifecycle_status`: watching / signal_generated / waiting_buy_point / buy_pending_confirm / trading / sell_signal_pending / sell_delayed / sold / pending_review / archived / invalid / blacklist / removed.
- `key_observe_price`: key observation price.
- `invalid_condition`: condition that invalidates the watch thesis.
- `risk_tags`: structured risk tags.
- `signal_enabled`: whether buy-point signal scanning is enabled.
- `latest_signal_id`: latest related signal id.
- `user_remark`: user note.

`pool_status`, `reason`, `labels`, `operation_strategies`, `buy_point_types`, `entry_price`, and `remark` remain as compatibility fields only. The active self-selected watch-pool flow no longer requires or derives decisions from `operation_strategies` / `buy_point_types`; it uses `trading_system`, `lifecycle_status`, `key_observe_price`, and `invalid_condition`.

#### `watch_pool_status_log` lifecycle fields

- `operation_type`: add_watch / adjust_observe_params / mark_invalid / confirm_buy / confirm_sell / archive / status_change.
- `snapshot`: JSON snapshot at the time of status change.

#### `watch_signal` lifecycle fields

- `trading_system`: trading system that generated the signal.
- `buy_point_confirmed`: whether the buy-point confirmation condition has been met.
- `buy_point_confirm_time`: buy-point confirmation time.
- `buy_point_confirm_price`: buy-point confirmation price.
- `abandoned_flag`: whether the user abandoned this opportunity.
- `abandoned_reason`: reason for abandoning this opportunity.
- `abandoned_time`: abandon time.
- `prevent_duplicate_signal`: whether equivalent future signals should be suppressed.
- `trigger_signature`: strategy-level deduplication signature.

#### `watch_trade` lifecycle fields

- `trading_system`: trading system used by this trade.
- `buy_reason`: user-confirmed buy reason.
- `trade_plan`: user-confirmed trade plan.
- `emotion_state`: user emotion state at confirmation time.

### Self-Selected Watch Pool Final Cleanup

- Trade Tab data source: `/api/h5/watch-trades/recent` or `/api/h5/watch-trades`.
- Trade list must not be synthesized from `watch_pool`.
- MVP sell flow supports full exit only. `watch_trade_execution.is_full_exit = true` is required for confirm-sell.
- Full exit updates `watch_trade.trade_status = completed`, writes a sell execution, updates the related watch to `pending_review`, and creates `review_trade` when missing.

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
- `mkt_hot_stock`: `trade_date + platform + stock_code`
- `mkt_daily_plate`: `trade_date + plate_type + platform + plate_code`
- `mkt_daily_plate_stock`: `plate_id + stock_code`
- `mkt_limit_up_stock`: `trade_date + source + stock_code`
- `mkt_stock_kline_daily`: `stock_code + trade_date + source`
- `mkt_stock_kline_15m`: `stock_code + kline_time + source`
- `watch_signal`: `stock_code + buy_point_type + signal_type + trigger_date`
- `watch_signal_performance`: `signal_id`
- `review_form`: `review_type + review_period`
- `config_notification_record`: `push_type + target_type + target_id + channel`

## Watch Lifecycle Indexes

- `watch_pool`: `stock_code + lifecycle_status`
- `watch_pool`: `trading_system`
- `watch_pool`: `latest_signal_id`
- `watch_pool_status_log`: `operation_type`
- `watch_signal`: `watch_id + signal_status`
- `watch_signal`: `trigger_signature`
- `watch_signal`: `trading_system`
- `watch_signal`: `abandoned_flag`
- `watch_trade`: `watch_id + trade_status`
- `watch_trade`: `trading_system`

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
- `mkt_daily_chance`
- `mkt_daily_chance_stock`
- `mkt_daily_tuyere`
- `mkt_daily_tuyere_stock`
- `mkt_hot_board`
- `mkt_limit_up_plate`

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
