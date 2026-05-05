from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import SESSION_TOKEN, require_login
from app.api.response import ok
from app.core.database import get_db
from app.models import ConfigDictionary, StockBasic, WatchPool
from app.services.normalization import normalize_stock_code, xueqiu_link
from app.services.prd_v1 import SeedService

router = APIRouter(prefix="/common", tags=["common"])


@router.post("/auth/login")
def login(payload: dict, db: Session = Depends(get_db)):
    SeedService(db).init_defaults()
    return ok({"token": SESSION_TOKEN, "user": {"user_id": "single-user", "nickname": "Aquant 用户", "role": "admin"}})


@router.post("/auth/logout")
def logout(user=Depends(require_login)):
    return ok({"logged_out": True})


@router.get("/auth/current-user")
def current_user(user=Depends(require_login)):
    return ok({"user_id": "single-user", "nickname": "Aquant 用户", "role": "admin"})


@router.get("/system/status")
def system_status(db: Session = Depends(get_db), user=Depends(require_login)):
    return ok(
        {
            "app": "Aquant",
            "mode": "single-user",
            "watch_count": db.query(WatchPool).count(),
        }
    )


@router.get("/dictionaries")
def dictionaries(dict_type: str | None = None, db: Session = Depends(get_db), user=Depends(require_login)):
    SeedService(db).init_defaults()
    query = db.query(ConfigDictionary).filter(ConfigDictionary.enabled.is_(True))
    if dict_type:
        query = query.filter(ConfigDictionary.dict_type == dict_type)
    rows = query.order_by(ConfigDictionary.dict_type, ConfigDictionary.sort_order).all()
    return ok([{"dict_id": row.dict_id, "dict_type": row.dict_type, "dict_label": row.dict_label, "dict_value": row.dict_value} for row in rows])


@router.get("/stocks/search")
def stock_search(keyword: str, db: Session = Depends(get_db), user=Depends(require_login)):
    query = db.query(StockBasic)
    if keyword:
        query = query.filter((StockBasic.stock_code.like(f"%{keyword}%")) | (StockBasic.stock_name.like(f"%{keyword}%")))
    return ok([{"stock_code": row.stock_code, "stock_name": row.stock_name, "xueqiu_url": xueqiu_link(row.stock_code)} for row in query.limit(20).all()])


@router.get("/stocks/{stock_code}/brief")
def stock_brief(stock_code: str, db: Session = Depends(get_db), user=Depends(require_login)):
    code = normalize_stock_code(stock_code)
    row = db.query(StockBasic).filter(StockBasic.stock_code == code).first()
    return ok({"stock_code": code, "stock_name": row.stock_name if row else code, "sector_name": row.sector_name if row else None, "xueqiu_url": xueqiu_link(code)})


@router.get("/stocks/{stock_code}/xueqiu-url")
def stock_xueqiu(stock_code: str, user=Depends(require_login)):
    try:
        return ok({"stock_code": normalize_stock_code(stock_code), "xueqiu_url": xueqiu_link(stock_code)})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
