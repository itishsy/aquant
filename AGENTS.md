# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Commands

### Backend (Python 3.12)
```bash
pip install -r requirements.txt          # Install dependencies
alembic upgrade head                     # Run system DB migrations
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pytest -v                                # Run all tests
pytest tests/test_prd_v1_api.py -v       # Run specific test file
```

### Frontend
```bash
cd frontend && npm install
npm run dev                              # Dev server on :5173
npm run build                            # Production build
npm run test                             # vitest
```

### Docker
```bash
docker compose up --build                # backend + frontend + redis
```

## Architecture

### Dual MySQL Database Layout
- **`a_quant`** (system DB): market data, watch pool, signals, trades, reviews, user preferences, config tables
- **`a_candle`** (K-line DB): `stock_kline_daily`, `stock_kline_15m`
- Both engines created in `app/core/database.py`. `SystemBase` / `CandleBase` are separate declarative bases.
- Migrations only cover `a_quant` (Alembic). K-line tables are auto-created on startup.

### API Route Structure

Three route modules mounted under `/api`:

| Prefix | File | Purpose |
|--------|------|---------|
| `/api/common` | `app/api/routes/common.py` | Auth (single-user login/logout), stock search/brief, dictionaries |
| `/api/h5` | `app/api/routes/h5.py` | Main H5 API: market overview, hot boards/stocks, limit-ups, watch pool CRUD, signals, trade confirm-buy/sell, reviews, user profile/preferences, notifications |
| `/api/admin` | `app/api/routes/admin_prd.py` | Admin dashboard, data sources, tasks, dictionaries, field mappings, strategies, logs, templates |

### Key Service Layer

- **`PrdWatchPoolService`** (`app/services/prd_v1.py`): Watch pool business logic (add/remove/blacklist/status transitions with logging)
- **`PrdMarketDataService`** (`app/services/prd_v1.py`): Market data aggregation queries
- **`SeedService`** (`app/services/prd_v1.py`): Idempotent seed data initialization (dictionaries, strategies, notification/review templates, tasks). Triggered on login or dictionary access.
- **`SignalEngine`** (`app/services/signal_engine.py`): Scans watch pool stocks against registered strategies to generate buy/risk signals
- **`KlineService`** (`app/services/kline.py`): K-line data retrieval for signal scanning
- **`ProviderFactory`** (`app/providers/factory.py`): Switches between `MockProvider` and `RealMarketProvider` based on `DATA_PROVIDER_MODE` setting

### Strategy Pattern
Strategies extend `StrategyBase` (`app/strategies/base.py`):
- `validate_preconditions(context)` → bool
- `generate_signal(context)` → dict | None
- Currently registered: `Macd15BullishDivergenceStrategy`, `HighVolumeRiskStrategy`, `BreakoutFailureStrategy`

### Auth Model
Single-user system. `app/api/deps.py` defines `require_login` — accepts Bearer token or `admin_token` header. In `dev` mode, unauthenticated requests are allowed. `require_admin` checks `X-Admin-Token` header.

### Frontend (React 18 + antd-mobile + echarts)

Routing in `App.tsx`: `/market`, `/watch-pool`, `/stocks/:stockCode`, `/trades/:tradeId/review`, `/reviews`, `/me`, `/settings`, `/admin/*`. Admin page has no bottom tabs.

API client (`frontend/src/api/client.ts`) auto-unwraps `{ success, data }` envelope from backend responses. Admin-token header hardcoded in dev mode.

### Test Architecture
- Tests use SQLite in-memory for both system and candle DBs, with `DATA_PROVIDER_MODE=mock`
- `conftest.py` sets environment variables before importing app modules, creates/drops all tables per test
- Uses FastAPI `TestClient` with `dependency_overrides` for DB sessions

## Key Constraints

- **No auto-trading**: System never places orders or connects to brokerage APIs
- **No K-line charts in H5**: Individual stock K-line viewing is redirected to Xueqiu (`xueqiu_link()` in `app/services/normalization.py`)
- **Manual watch pool only**: All watch pool entries are manually added by the user
- **Market data display**: Only raw objective fields, no subjective scores (Market/Sector/Watch Score)
- **All signals are advisory** only, marked with `ASSISTANT_NOTE` ("仅作为交易辅助，请结合个人交易规则确认。")

## Environment Configuration

Copy `.env.example` to `.env`. Key variables:
- `DATABASE_URL` / `CANDLE_DATABASE_URL` — MySQL connections (point to `8.148.181.1:3306`)
- `DATA_PROVIDER_MODE` — `mock` (dev) or `real`
- `ADMIN_TOKEN` — default `dev-admin-token`
- `ENABLE_SCHEDULER` — controls APScheduler (default `false`)
- `APP_ENV` — `dev` disables auth checks
