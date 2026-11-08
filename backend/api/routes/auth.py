"""Authentication endpoints."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

from ..config import settings
from ..services.auth import (
    authorization_url,
    create_session_token,
    create_state,
    current_user,
    exchange_code,
    upsert_google_user,
    validate_state,
    verify_id_token,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/google/login")
def google_login() -> RedirectResponse:
    return RedirectResponse(authorization_url(create_state()))


@router.get("/google/callback")
async def google_callback(code: str, state: str) -> RedirectResponse:
    validate_state(state)
    tokens = await exchange_code(code)
    claims = await verify_id_token(tokens.get("id_token", ""))
    user = upsert_google_user(claims)
    response = RedirectResponse(settings.frontend_origin + "/?view=workout")
    response.set_cookie(
        settings.auth_cookie_name,
        create_session_token(user),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=3600,
        path="/",
    )
    return response


@router.post("/logout")
def logout() -> JSONResponse:
    response = JSONResponse({"status": "logged_out"})
    response.delete_cookie(
        settings.auth_cookie_name,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
    return response


@router.get("/me")
def me(request: Request) -> dict[str, object]:
    user = current_user(request)
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "picture_url": user.picture_url,
    }
