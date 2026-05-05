from __future__ import annotations

from fastapi import Header, HTTPException

from app.core.config import get_settings


SESSION_TOKEN = "single-user-token"


def require_login(authorization: str | None = Header(default=None)):
    if authorization in {f"Bearer {SESSION_TOKEN}", get_settings().admin_token}:
        return {"user_id": "single-user", "role": "admin"}
    # Keep local development usable while still providing a clear single-user boundary.
    if get_settings().app_env == "dev" and authorization is None:
        return {"user_id": "single-user", "role": "admin"}
    raise HTTPException(status_code=401, detail="UNAUTHORIZED")


def require_admin(user=Header(default=None), x_admin_token: str | None = Header(default=None)):
    if x_admin_token == get_settings().admin_token:
        return {"user_id": "single-user", "role": "admin"}
    return require_login(user)
