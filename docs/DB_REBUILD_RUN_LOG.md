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
