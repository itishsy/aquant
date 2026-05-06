# DB Rebuild Run Log

Date: 2026-05-05

Mode: PRD v1 clean database rebuild.

## Phase 0 Startup Check

- Git status: dirty. The dirty state is from the previous PRD v1 hard cleanup and includes deleted legacy files, archived old docs/migrations, rewritten PRD v1 models/services/tests, and generated cleanup documents.
- `.env`: not present in workspace.
- `.env.example`: present and points to remote MySQL:
  - system DB: `a_quant`
  - candle DB: `a_candle`
- Backend dependency file: `requirements.txt` present.
- Frontend dependency file: `frontend/package.json` present.
- Docker compose: `docker-compose.yml` present.
- Active migration: `alembic/versions/20260505_0001_prd_v1_baseline.py`.
- Archived old migrations: `alembic/archive_old/`.
- Current registered API routers: `/api/common/**`, `/api/h5/**`, `/api/admin/**`.

## PRD Guardrails

- Do not recreate old MVP/v1.1 tables.
- Do not reintroduce automatic watch-pool insertion.
- Do not reintroduce Market Score, Sector Score, Watch Score, daily plan, checklist, or strict mode.
- K-line tables are backend-only and must not power an H5 internal K-line chart.

## Pending

- Inspect ORM and migration for old table references.
- Rebuild remote MySQL schemas with PRD v1 baseline.
- Initialize seed data.
- Initialize PRD-safe mock data.
- Start backend, H5 frontend, and admin frontend entry.
- Run smoke tests.

## Phase 1 Model And Migration Check

- Scanned active ORM, migrations, services, and tests for forbidden legacy table/model references.
- Active migration: `alembic/versions/20260505_0001_prd_v1_baseline.py`.
- Fixed Alembic MySQL URL handling by escaping `%` in `alembic/env.py`; this is required because the configured password contains URL-encoded `%40`.
- Rewrote `app/services/prd_v1.py` seed labels/templates to clean PRD v1 Chinese values.
- Added `app/services/mock_data.py` for idempotent PRD-safe development data.
- Added `frontend/src/pages/AdminPage.tsx` and `/admin/*` route; admin pages do not show H5 bottom tabs.

## Phase 2 Database Rebuild

Executed:

```powershell
python -m alembic upgrade head
```

Result: success on remote MySQL `a_quant`.

Final `a_quant` tables:

- `alembic_version`
- `stock_basic`
- `mkt_daily`
- `mkt_hot_board`
- `mkt_hot_stock`
- `mkt_limit_up`
- `mkt_stock_kline_daily`
- `mkt_stock_kline_15m`
- `watch_pool`
- `watch_signal`
- `watch_signal_performance`
- `watch_pool_status_log`
- `watch_trade`
- `watch_trade_execution`
- `review_form`
- `review_weekly`
- `review_monthly`
- `review_trade`
- `my_user_profile`
- `my_user_preference`
- `my_notification_setting`
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

`a_candle` final state: empty. Old `stock_kline_daily` and `stock_kline_15m` were dropped before rebuild because they are forbidden legacy tables.

Forbidden old tables found after rebuild: none.

Missing required PRD v1 tables after rebuild: none.

## Phase 3 Seed Data

Executed:

```powershell
python -c "from app.core.database import SystemSessionLocal; from app.services.prd_v1 import SeedService; db=SystemSessionLocal(); print(SeedService(db).init_defaults()); db.close()"
```

Result:

- First run: `{'created': 71}`
- Re-run: `{'created': 0}`

Seed data is idempotent.

## Phase 4 Mock Data

Executed:

```powershell
python -c "from app.core.database import SystemSessionLocal; from app.services.mock_data import MockDataService; db=SystemSessionLocal(); print(MockDataService(db).init_all()); db.close()"
```

Result:

- `stock_basic`: 12
- `mkt_daily`: 3
- `mkt_hot_board`: 6
- `mkt_hot_stock`: 30
- `mkt_limit_up`: 10
- `watch_pool`: 2 manual demo records
- `watch_signal`: 2
- `watch_trade`: 1
- `review`: 3
- `notification`: 1

Re-run did not create duplicate market/hot/limit/signal/trade/review/notification records.

## Phase 5 Backend Startup And API Smoke

Port `8000` was occupied by an old Python process that Windows refused to terminate. To avoid testing against stale state, the current backend was started on `127.0.0.1:8001`.

Backend command:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

API smoke result: passed.

Verified endpoints:

- `GET /api/common/system/status`
- `GET /api/common/dictionaries`
- `GET /api/h5/market/trading-dates`
- `GET /api/h5/market/overview?trade_date=2026-05-06`
- `GET /api/h5/market/hot-stocks?trade_date=2026-05-06`
- `GET /api/h5/market/limit-ups?trade_date=2026-05-06`
- `GET /api/h5/watch-pool/summary`
- `GET /api/h5/watch-signals/recent`
- `GET /api/h5/watch-trades/recent`
- `GET /api/h5/reviews/todos`
- `GET /api/h5/me/backend-entry`
- `GET /api/admin/dashboard/overview`
- `GET /api/admin/tasks`
- `GET /api/admin/dictionaries`
- `GET /api/admin/task-logs`

## Phase 6 H5 Frontend Startup

Build:

```powershell
npm.cmd run build
```

Result: passed.

Dev server:

```powershell
set VITE_API_BASE_URL=http://127.0.0.1:8001/api && npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

Result: started on `http://127.0.0.1:5173`.

HTTP page smoke:

- `/market`: 200
- `/watch-pool`: 200
- `/reviews`: 200
- `/me`: 200

## Phase 7 Admin Frontend Startup

Admin frontend is part of the same Vite app, exposed at:

- `http://127.0.0.1:5173/admin`

HTTP page smoke:

- `/admin`: 200

Admin is outside H5 bottom navigation.

## Phase 8 Tests

- `python -m compileall app tests`: passed.
- `python -m pytest -q`: passed, 15 tests.
- `npm.cmd run build`: passed.
- `npm.cmd run test`: passed, 1 test.
- Docker validation: not run because Docker CLI is not installed in the current environment.

## Phase 9 Final Checklist

- Database rebuilt successfully: yes.
- Forbidden old tables: none.
- Required PRD v1 tables: all present in `a_quant`.
- Seed data initialized: yes.
- Mock data initialized: yes.
- Backend started: yes, `http://127.0.0.1:8001`.
- H5 started: yes, `http://127.0.0.1:5173`.
- Admin started: yes, `http://127.0.0.1:5173/admin`.
- H5 bottom tabs: market, watch, review, my.
- Admin not in H5 bottom nav: yes.
- Market has mock data: yes.
- Watch has observation/signal/trade data: yes.
- Review has weekly/monthly/trade sample data: yes.
- My page has admin entry: yes.
- API smoke test: passed.
- Old automatic watch-pool insertion / automatic trading / subjective score routes: not present in active source scan.
