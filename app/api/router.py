from fastapi import APIRouter

from app.api.routes import admin_prd, common, h5

api_router = APIRouter()
api_router.include_router(common.router)
api_router.include_router(h5.router)
api_router.include_router(admin_prd.router)
