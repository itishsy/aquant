# PRD v1 Hard Cleanup Final Report

Date: 2026-05-05

Branch: `cleanup-prd-v1-hard`

## Conclusion

Result: basically complete.

The repository has been hard-cleaned around the latest `Aquant PRD v1.0.md`. Active backend routes, active H5 routes, SQLAlchemy models, Alembic baseline, tests, and task logging now target the latest PRD v1 scope.

One practical note: this is a development reset. Local development databases should be rebuilt from the new PRD v1 baseline migration. If real business data is later found, use a safe data migration instead of dropping old tables directly.

## Removed Old Capabilities

- Automatic watch-pool insertion and auto candidate flows.
- Market Score, Sector Score, Watch Score, comprehensive hot-stock scoring, resonance bonus, and risk-deduction ranking.
- v1.1 daily trade plan, checklist, strict mode, sell-plan table, and trading ability scoring.
- Old `/api/market`, `/api/sectors`, `/api/hot-stocks`, `/api/limit-up`, `/api/watch-pool`, `/api/stocks`, `/api/signals`, `/api/trades`, `/api/reviews`, and `/api/v1_1` style routes.
- In-H5 K-line chart component and old standalone pages outside the four primary H5 areas.
- Old tests that asserted deleted MVP/v1.1 behavior.

## Deleted Or Archived Code Files

### Deleted API Route Files

- `app/api/routes/admin.py`
- `app/api/routes/market.py`
- `app/api/routes/sectors.py`
- `app/api/routes/hot_stocks.py`
- `app/api/routes/limit_up.py`
- `app/api/routes/watch_pool.py`
- `app/api/routes/stocks.py`
- `app/api/routes/signals.py`
- `app/api/routes/trades.py`
- `app/api/routes/reviews.py`
- `app/api/routes/v1_1.py`

### Deleted Service Files

- `app/services/market.py`
- `app/services/sector.py`
- `app/services/hot_stock.py`
- `app/services/limit_up.py`
- `app/services/market_review.py`
- `app/services/watch_pool.py`
- `app/services/trade.py`
- `app/services/review.py`
- `app/services/v1_1.py`

### Deleted Frontend Files

- `frontend/src/pages/DailyPlanPage.tsx`
- `frontend/src/pages/SectorsPage.tsx`
- `frontend/src/pages/SignalsPage.tsx`
- `frontend/src/pages/TradesPage.tsx`
- `frontend/src/pages/MonthlyReviewPage.tsx`
- `frontend/src/components/LineChart.tsx`

### Deleted Test Files

- `tests/test_api.py`
- `tests/test_market.py`
- `tests/test_hot_stock.py`
- `tests/test_watch_pool.py`
- `tests/test_trade_review.py`
- `tests/test_signal_engine.py`
- `tests/test_v1_1_flow.py`

## Archived Documents And Migrations

Archived to `docs/archive/old-prd/`:

- Old MVP implementation logs/plans.
- Old v1.1 upgrade documents.
- Old final PRD gap/excess cleanup drafts.
- Old real-data collection notes.

Archived to `alembic/archive_old/`:

- `20260426_0001_init_mvp.py`
- `20260430_0002_v1_1_incremental.py`
- `20260505_0003_prd_v1_alignment.py`

## Database Cleanup

Active baseline migration:

- `alembic/versions/20260505_0001_prd_v1_baseline.py`

Final active table families:

- `mkt_*`
- `watch_*`
- `review_*`
- `my_*`
- `config_*`
- `stock_basic`

Old table families removed from active models:

- `market_daily`, `sector_daily`, `hot_stock_rank`, `limit_up_daily`
- `stock_kline_daily`, `stock_kline_15m`
- `signal_record`, `trade_record`, `trade_review`, `strategy_config`, `system_task_log`
- v1.1 tables including `watch_pool_score`, `daily_trade_plan`, `trade_execution_checklist`, `sell_plan`, `discipline_rule`, `user_trading_score`

## Active API Scope

Only these API prefixes are registered:

- `/api/common/**`
- `/api/h5/**`
- `/api/admin/**`

The main active PRD APIs include:

- `/api/common/auth/*`
- `/api/common/system/status`
- `/api/common/dictionaries`
- `/api/common/stocks/*`
- `/api/h5/market/*`
- `/api/h5/watch-pool/*`
- `/api/h5/watch-signals/*`
- `/api/h5/watch-trades/*`
- `/api/h5/reviews/*`
- `/api/h5/me/*`
- `/api/h5/notifications/*`
- `/api/admin/*`

## Active Page Scope

H5 routes are limited to the PRD v1 product areas:

- `/market`
- `/watch-pool`
- `/stocks/:stockCode`
- `/trades/:tradeId/review`
- `/reviews`
- `/me`
- `/settings`

The deleted K-line chart means stock detail should continue to use Xueqiu links for market/K-line viewing.

## Deprecated / Kept With Reason

- `app/providers/real_provider.py`: kept because the user previously requested real market data collection. It contains a negative compliance statement about not using browser automation, account login, broker integration, or anti-scraping bypass. It is not an automatic trading/broker route.
- Compliance documents still mention prohibited words as blocked-term lists. These are documentation guardrails, not product copy.

## Validation Results

| Command | Result |
|---|---|
| `python -m compileall app tests` | Passed |
| `python -m pytest -q` | Passed, 15 tests |
| `npm.cmd run build` | Passed |
| `npm.cmd run test` | Passed, 1 test |
| `alembic upgrade head` on clean SQLite | Passed |
| PRD v1 seed initialization on clean SQLite | Passed, 62 records created |

Warnings:

- FastAPI `on_event` deprecation warnings remain.
- SQLAlchemy/default `datetime.utcnow` deprecation warnings remain.

These warnings do not block PRD v1 acceptance, but they are good candidates for a follow-up technical-debt pass.

## Compliance Result

- No automatic order placement route was found.
- No broker trading interface route was found.
- No automatic watch-pool insertion remains in active source.
- H5 no longer has an internal K-line chart component.
- Market data active flow is raw data oriented.
- Hot stocks keep source/platform ranking and score.
- Watch-pool creation is manual and idempotent.
- Confirm buy/sell writes internal records only and requires user action.
- Task logs use `config_task_log`.
- Admin writes use operation logging via `config_operation_log` where implemented.

## Recommended Next Steps

1. Reinitialize local development databases from the PRD v1 baseline.
2. Run a browser smoke test across Market, Watch, Review, and My.
3. Add a small automated route-list test to prevent old `/api/v1` or `/api/market` routes from returning.
4. Replace `datetime.utcnow` with timezone-aware timestamps.
5. Consider whether generated files like `frontend/dist` and local DBs should be permanently ignored if they are not already.
