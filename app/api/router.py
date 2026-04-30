from fastapi import APIRouter

from app.api.routes import admin, health, hot_stocks, limit_up, market, reviews, sectors, signals, stocks, trades, v1_1, watch_pool

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(market.router)
api_router.include_router(sectors.router)
api_router.include_router(hot_stocks.router)
api_router.include_router(limit_up.router)
api_router.include_router(watch_pool.router)
api_router.include_router(stocks.router)
api_router.include_router(signals.router)
api_router.include_router(trades.router)
api_router.include_router(reviews.router)
api_router.include_router(admin.router)
api_router.include_router(v1_1.router)
