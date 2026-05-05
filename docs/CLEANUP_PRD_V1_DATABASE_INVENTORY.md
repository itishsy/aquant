# PRD v1 Database Inventory

Mode: `hard_dev_reset`

Reason: this cleanup is for a development-stage repository. No production-data marker was found. Local SQLite files such as `test_aquant.db` and `test_a_candle.db` were treated as test artifacts.

## KEEP Tables

| Table | Purpose |
|---|---|
| `stock_basic` | Stock search and brief information |
| `mkt_daily` | Raw daily market overview |
| `mkt_hot_board` | Platform raw hot-board records |
| `mkt_hot_stock` | Platform raw hot-stock records |
| `mkt_limit_up` | Platform raw limit-up records |
| `mkt_stock_kline_daily` | Backend-only daily K-line calculation |
| `mkt_stock_kline_15m` | Backend-only 15-minute K-line calculation |
| `watch_pool` | Manually added watch pool |
| `watch_pool_status_log` | Watch-pool status changes |
| `watch_signal` | Watch signal records |
| `watch_signal_performance` | Signal follow-up performance |
| `watch_trade` | Trade master record |
| `watch_trade_execution` | Buy/sell execution ledger |
| `review_form` | Unified weekly/monthly/trade review form |
| `review_weekly` | Weekly review details |
| `review_monthly` | Monthly review details |
| `review_trade` | Single-trade review card |
| `my_user_profile` | Single-user profile |
| `my_user_preference` | User preferences |
| `my_notification_setting` | Notification preferences |
| `config_data_source` | Data source configuration |
| `config_task` | Task configuration |
| `config_task_log` | Task execution logs |
| `config_field_mapping` | Field mapping configuration |
| `config_dictionary` | Business dictionaries |
| `config_strategy` | Strategy configuration |
| `config_notification_template` | Notification templates |
| `config_notification_record` | Site notification records |
| `config_review_template` | Review templates |
| `config_operation_log` | Admin operation logs |
| `alembic_version` | Migration metadata |

## Removed From Active Models

| Old Table | Reason |
|---|---|
| `market_daily` | Old subjective Market Score table |
| `sector_daily` | Old subjective Sector Score table |
| `hot_stock_rank` | Old comprehensive hot-score table |
| `limit_up_daily` | Replaced by `mkt_limit_up` |
| `stock_kline_daily` | Replaced by `mkt_stock_kline_daily` |
| `stock_kline_15m` | Replaced by `mkt_stock_kline_15m` |
| `signal_record` | Replaced by `watch_signal` |
| `strategy_config` | Replaced by `config_strategy` |
| `trade_record` | Replaced by `watch_trade` and `watch_trade_execution` |
| `trade_review` | Replaced by `review_trade` |
| `system_task_log` | Replaced by `config_task_log` |
| `watch_pool_lifecycle` | v1.1 lifecycle feature not in latest PRD |
| `watch_pool_score` | v1.1 Watch Score feature not in latest PRD |
| `daily_trade_plan` | v1.1 daily-plan feature not in latest PRD |
| `daily_trade_plan_item` | v1.1 daily-plan feature not in latest PRD |
| `trade_execution_checklist` | v1.1 checklist feature not in latest PRD |
| `sell_plan` | v1.1 sell-plan table not in latest PRD |
| `trade_error_tag` | v1.1 detailed error-tag table not in latest PRD |
| `trade_review_detail` | v1.1 review-detail table not in latest PRD |
| `weekly_review` | Replaced by `review_weekly` |
| `monthly_review` | Replaced by `review_monthly` |
| `discipline_rule` | v1.1 strict/discipline mode not in latest PRD |
| `user_trading_score` | v1.1 ability scoring not in latest PRD |

## Current Baseline Migration

- Active baseline: `alembic/versions/20260505_0001_prd_v1_baseline.py`
- Archived migrations: `alembic/archive_old/`
- Validation: `alembic upgrade head` passed against a clean SQLite database.
- Seed validation: PRD v1 seed initialization passed and created 62 records on a clean SQLite database.

## Rebuild Recommendation

For local development databases, rebuild from the PRD v1 baseline:

```powershell
$env:DATABASE_URL='sqlite:///./aquant_prd_v1.db'
$env:CANDLE_DATABASE_URL='sqlite:///./aquant_candle_prd_v1.db'
python -m alembic upgrade head
```

If real business data is later discovered, pause hard reset and write a safe migration to copy usable data into the PRD v1 tables before dropping old tables.
