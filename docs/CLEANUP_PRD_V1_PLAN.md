# PRD v1 Hard Cleanup Plan

Mode: `HARD_CLEAN` / `hard_dev_reset`

Snapshot commit: `1f48d39 snapshot before hard cleanup for PRD v1`

Branch: `cleanup-prd-v1-hard`

## Latest PRD Whitelist

### API Prefixes

- KEEP `/api/common/**`
- KEEP `/api/h5/**`
- KEEP `/api/admin/**`

### H5 Pages

- KEEP market page: overview, hot stocks, limit-up list.
- KEEP watch page: observation, signals, trades.
- KEEP review page: weekly review, monthly review, single-trade review entry.
- KEEP my page: profile, todos, preferences, system summary, admin entry.

### Admin Pages

- KEEP dashboard.
- KEEP data source management.
- KEEP collection task management.
- KEEP field mapping management.
- KEEP strategy management.
- KEEP dictionary management.
- KEEP review template management.
- KEEP notification management.
- KEEP log center.
- KEEP account and security.

### Tables

- KEEP `mkt_daily`, `mkt_hot_board`, `mkt_hot_stock`, `mkt_limit_up`, `mkt_stock_kline_daily`, `mkt_stock_kline_15m`.
- KEEP `watch_pool`, `watch_signal`, `watch_signal_performance`, `watch_pool_status_log`, `watch_trade`, `watch_trade_execution`.
- KEEP `review_form`, `review_weekly`, `review_monthly`, `review_trade`.
- KEEP `my_user_profile`, `my_user_preference`, `my_notification_setting`.
- KEEP `config_data_source`, `config_task`, `config_task_log`, `config_field_mapping`, `config_dictionary`, `config_strategy`, `config_notification_template`, `config_notification_record`, `config_review_template`, `config_operation_log`.
- KEEP `stock_basic` as stock search/brief support.

## Cleanup Categories

| Object | Category | Reason | Risk | Verification |
|---|---|---|---|---|
| Old non-PRD route files | DELETE | Outside `/api/common`, `/api/h5`, `/api/admin` | Medium | compileall, pytest |
| Old scoring services | DELETE | Market/Sector/Watch Score conflict with latest PRD | Medium | PRD market tests |
| Old v1.1 daily-plan/checklist/strict-mode services | DELETE | Not in latest PRD | Medium | pytest |
| Old standalone H5 pages | DELETE | H5 bottom nav must be market/watch/review/my | Low | npm build |
| In-H5 K-line chart component | DELETE | K-line is backend-only and Xueqiu link is used for viewing | Low | npm build, keyword scan |
| Old v1.1/MVP tests | DELETE/REWRITE | Assert deleted behavior | Low | pytest |
| Old MVP/v1.1 docs | ARCHIVE | Historical context only | Low | doc inventory |
| Old migrations | ARCHIVE | Replaced by PRD v1 baseline in dev reset mode | Medium | alembic upgrade head |
| Old tables/models | DROP_TABLE via baseline reset | Replaced by PRD v1 schema | High | clean SQLite migration |
| Generated artifacts | DELETE | Not source code | Low | rebuild/test |

## Database Handling

No production-data marker was found in the workspace. Local SQLite DBs were test artifacts.

Actions:

1. Archive old migrations to `alembic/archive_old/`.
2. Rewrite SQLAlchemy models to PRD v1 baseline tables only.
3. Add a PRD v1 baseline migration.
4. Remove local test DB artifacts.
5. Validate `alembic upgrade head` against clean SQLite.
6. Validate seed initialization against clean SQLite.

## Safety Rules

- Do not remove database connection/configuration, provider abstractions, mock provider, unified response helpers, auth foundation, test fixtures, or current PRD tables.
- If production data is later discovered, do not use the dev reset directly; switch to a safe migration that copies usable data into PRD v1 tables before dropping old tables.
