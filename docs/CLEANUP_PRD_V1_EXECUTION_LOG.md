# PRD v1 Hard Cleanup Execution Log

Date: 2026-05-05

Mode: `HARD_CLEAN` / `hard_dev_reset`

## Safety Snapshot

- Created snapshot commit before cleanup: `1f48d39 snapshot before hard cleanup for PRD v1`.
- Created cleanup branch: `cleanup-prd-v1-hard`.
- No production-data marker was found in the local workspace. Local SQLite files were treated as test artifacts.

## Inventory And Plan

- Generated `docs/CLEANUP_PRD_V1_CODE_INVENTORY.md`.
- Generated `docs/CLEANUP_PRD_V1_DATABASE_INVENTORY.md`.
- Generated `docs/CLEANUP_PRD_V1_DOC_INVENTORY.md`.
- Generated `docs/CLEANUP_PRD_V1_PLAN.md`.

## Documents

- Archived old MVP/v1.1/legacy implementation documents to `docs/archive/old-prd/`.
- Kept latest PRD-facing documents and cleanup documents.
- Preserved prohibited-word mentions only in compliance/checklist contexts where they describe blocked terms.

## API Routes

- Removed old business routers outside the PRD v1 prefixes:
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
  - `app/api/routes/admin.py`
- Rewrote route registration so only `/api/common/**`, `/api/h5/**`, `/api/admin/**` are registered by `app/api/router.py`.

## Backend Services

- Removed old scoring/legacy services:
  - `app/services/market.py`
  - `app/services/sector.py`
  - `app/services/hot_stock.py`
  - `app/services/limit_up.py`
  - `app/services/market_review.py`
  - `app/services/watch_pool.py`
  - `app/services/trade.py`
  - `app/services/review.py`
  - `app/services/v1_1.py`
- Rewrote `app/services/prd_v1.py` as the PRD v1 service layer for seed data, market reads, manual watch-pool operations, and operation logs.
- Rewrote `app/services/tasks.py` so task logs write to `config_task_log` and no automatic watch-pool insertion remains.
- Rewrote `app/services/kline.py` to use `mkt_stock_kline_daily` and `mkt_stock_kline_15m` as backend-only K-line tables.
- Rewrote `app/services/signal_engine.py` to generate signals only for manually added watch-pool records with monitoring enabled.
- Cleaned strategy text in `app/strategies/macd15.py` and `app/strategies/risk.py`.

## Frontend

- Removed PRD-conflicting pages/components:
  - `frontend/src/pages/DailyPlanPage.tsx`
  - `frontend/src/pages/SectorsPage.tsx`
  - `frontend/src/pages/SignalsPage.tsx`
  - `frontend/src/pages/TradesPage.tsx`
  - `frontend/src/pages/MonthlyReviewPage.tsx`
  - `frontend/src/components/LineChart.tsx`
- Updated `frontend/src/App.tsx` to expose only current H5 routes:
  - `/market`
  - `/watch-pool`
  - `/stocks/:stockCode`
  - `/trades/:tradeId/review`
  - `/reviews`
  - `/me`
  - `/settings`

## Database And Migrations

- Archived old migrations to `alembic/archive_old/`.
- Rewrote SQLAlchemy entities to PRD v1 baseline tables only.
- Added `alembic/versions/20260505_0001_prd_v1_baseline.py`.
- Removed old model classes for Market Score, Sector Score, Watch Score, daily plans, strict mode, checklist, and old trade/review tables.
- Verified `alembic upgrade head` against clean SQLite.
- Verified seed initialization against clean SQLite.

## Tests

- Deleted old tests for MVP/v1.1/scoring/daily-plan/strict-mode flows.
- Rewrote `tests/test_prd_v1_api.py` to cover current PRD flow:
  - market raw data
  - raw hot-stock ranking
  - raw limit-up reason
  - manual watch add idempotency
  - confirm buy creates `watch_trade` and `watch_trade_execution`
  - duplicate confirm-buy protection
  - confirm sell creates execution and trade review
  - weekly review API exposure

## Global Keyword Scan

- Source scan found no active routes/services/pages for automatic watch-pool insertion, subjective score systems, daily trade plan, strict mode, checklist, broker order routing, or in-H5 K-line chart display.
- Remaining `broker` hit is in `app/providers/real_provider.py` as a negative compliance statement.
- Remaining prohibited-word hits are in README/compliance/checklist documents as blocked-term descriptions.

## Validation

- `python -m compileall app tests`: passed.
- `python -m pytest -q`: passed, 15 tests.
- `npm.cmd run build`: passed.
- `npm.cmd run test`: passed, 1 test.
- `alembic upgrade head` on clean SQLite: passed.
- Seed initialization on clean SQLite: passed, 62 records created.

## Generated Artifacts Removed

- Removed local test DB files, cleanup check DBs, `frontend/dist`, Vitest result cache, `gcm-diagnose.log`, and `__pycache__` directories after validation.
