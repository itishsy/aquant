from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import CandleBase, SystemBase, candle_engine, system_engine


settings = get_settings()
app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    SystemBase.metadata.create_all(bind=system_engine)
    CandleBase.metadata.create_all(bind=candle_engine)


app.include_router(api_router, prefix=settings.api_prefix)
