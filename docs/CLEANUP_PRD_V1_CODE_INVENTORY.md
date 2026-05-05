# PRD v1 Code Inventory

This inventory reflects the post-cleanup active source classification.

## Backend Routes

| File | Category | Reason |
|---|---|---|
| `app/api/routes/common.py` | KEEP | `/api/common/**` |
| `app/api/routes/h5.py` | KEEP | `/api/h5/**` |
| `app/api/routes/admin_prd.py` | KEEP | `/api/admin/**` |
| `app/api/routes/health.py` | KEEP | App-level health route file retained, not registered as old business API |
| `app/api/routes/admin.py` | DELETE | Old admin/task route |
| `app/api/routes/market.py` | DELETE | Old `/api/market` route |
| `app/api/routes/sectors.py` | DELETE | Old sector-score route |
| `app/api/routes/hot_stocks.py` | DELETE | Old comprehensive hot-stock route |
| `app/api/routes/limit_up.py` | DELETE | Old limit-up route |
| `app/api/routes/watch_pool.py` | DELETE | Old watch-pool route |
| `app/api/routes/stocks.py` | DELETE | Old stock/K-line route |
| `app/api/routes/signals.py` | DELETE | Old signal route |
| `app/api/routes/trades.py` | DELETE | Old trade route |
| `app/api/routes/reviews.py` | DELETE | Old review route |
| `app/api/routes/v1_1.py` | DELETE | v1.1-only route |

## Backend Services

| File | Category | Reason |
|---|---|---|
| `app/services/prd_v1.py` | KEEP/REWRITE | PRD v1 seed, market, watch-pool, and operation-log services |
| `app/services/normalization.py` | KEEP | Stock code and Xueqiu URL support |
| `app/services/indicator.py` | KEEP | Backend-only indicator calculations |
| `app/services/kline.py` | KEEP/REWRITE | Backend-only K-line collection using `mkt_*` tables |
| `app/services/quality.py` | KEEP/REWRITE | Data quality and task-error logging with PRD tables |
| `app/services/tasks.py` | KEEP/REWRITE | PRD v1 task logging with `config_task_log` |
| `app/services/signal_engine.py` | KEEP/REWRITE | Manual watch-pool signal scanner |
| `app/services/market.py` | DELETE | Old market score service |
| `app/services/sector.py` | DELETE | Old sector score service |
| `app/services/hot_stock.py` | DELETE | Old comprehensive hot-stock service |
| `app/services/limit_up.py` | DELETE | Old limit-up service |
| `app/services/market_review.py` | DELETE | Old market review service |
| `app/services/watch_pool.py` | DELETE | Old auto-add-capable watch service |
| `app/services/trade.py` | DELETE | Old `trade_record` service |
| `app/services/review.py` | DELETE | Old review service |
| `app/services/v1_1.py` | DELETE | v1.1 daily-plan/checklist/strict-mode service |

## Models And Migrations

| File | Category | Reason |
|---|---|---|
| `app/models/entities.py` | KEEP/REWRITE | PRD v1 baseline entities only |
| `alembic/versions/20260505_0001_prd_v1_baseline.py` | KEEP | PRD v1 clean baseline migration |
| `alembic/archive_old/*` | ARCHIVE | Historical migrations retained for reference |

## Frontend

| File | Category | Reason |
|---|---|---|
| `frontend/src/pages/MarketPage.tsx` | KEEP | Market page |
| `frontend/src/pages/WatchPoolPage.tsx` | KEEP | Watch/signals/trades page |
| `frontend/src/pages/ReviewsPage.tsx` | KEEP | Weekly/monthly review page |
| `frontend/src/pages/SettingsPage.tsx` | KEEP | Current My/settings page |
| `frontend/src/pages/StockDetailPage.tsx` | KEEP | Stock detail with Xueqiu link |
| `frontend/src/pages/TradeReviewDetailPage.tsx` | KEEP | Single-trade review entry |
| `frontend/src/pages/DailyPlanPage.tsx` | DELETE | v1.1 daily plan |
| `frontend/src/pages/SectorsPage.tsx` | DELETE | Old sector page |
| `frontend/src/pages/SignalsPage.tsx` | DELETE | Old standalone signal page |
| `frontend/src/pages/TradesPage.tsx` | DELETE | Old standalone trade page |
| `frontend/src/pages/MonthlyReviewPage.tsx` | DELETE | Folded into review scope |
| `frontend/src/components/LineChart.tsx` | DELETE | No internal H5 K-line chart |

## Tests

| File | Category | Reason |
|---|---|---|
| `tests/test_prd_v1_api.py` | KEEP/REWRITE | Current PRD v1 API flow |
| `tests/test_normalization.py` | KEEP | Stock code and Xueqiu URL support |
| `tests/test_quality.py` | KEEP | Data quality support |
| `tests/test_api.py` | DELETE | Old API assumptions |
| `tests/test_market.py` | DELETE | Old market-score assumptions |
| `tests/test_hot_stock.py` | DELETE | Old hot-score assumptions |
| `tests/test_signal_engine.py` | DELETE | Old signal engine dependencies |
| `tests/test_trade_review.py` | DELETE | Old trade-review tables |
| `tests/test_v1_1_flow.py` | DELETE | v1.1-only flow |
| `tests/test_watch_pool.py` | DELETE | Old watch-pool service |

## Generated Artifacts

| Path | Category | Reason |
|---|---|---|
| `**/__pycache__/**` | DELETE | Generated Python cache |
| `frontend/dist/**` | DELETE | Generated frontend build output |
| `frontend/node_modules/.vite/**` | DELETE | Generated Vite/Vitest cache |
| `test_aquant.db`, `test_a_candle.db` | DELETE | Local test DB artifacts |
| `gcm-diagnose.log` | DELETE | Local diagnostic log |
