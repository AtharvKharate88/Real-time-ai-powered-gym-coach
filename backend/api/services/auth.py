"""Google OIDC and application-session helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import HTTPException, Request
from sqlalchemy import select

from database.session import SessionLocal
from models import User

from ..config import settings

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUER = "https://accounts.google.com"
STATE_TTL_SECONDS = 600
SESSION_TTL_SECONDS = 3600


def _require_config() -> None:
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured.")
    if len(settings.session_secret) < 32:
        raise HTTPException(status_code=503, detail="SESSION_SECRET is not configured.")


def _sign(value: str) -> str:
    digest = hmac.new(
        settings.session_secret.encode(),
        value.encode(),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def create_state() -> str:
    _require_config()
    payload = f"{int(time.time())}.{secrets.token_urlsafe(24)}"
    return f"{payload}.{_sign(payload)}"


def validate_state(state: str) -> None:
    try:
        timestamp, nonce, signature = state.split(".", 2)
        payload = f"{timestamp}.{nonce}"
        issued_at = int(timestamp)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid OAuth state.") from None
    if time.time() - issued_at > STATE_TTL_SECONDS or not hmac.compare_digest(
        signature, _sign(payload)
    ):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state.")


def authorization_url(state: str) -> str:
    return GOOGLE_AUTH_URL + "?" + urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
    )


async def exchange_code(code: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    if response.is_error:
        raise HTTPException(status_code=502, detail="Google token exchange failed.")
    return response.json()


async def verify_id_token(id_token: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(GOOGLE_JWKS_URL)
    response.raise_for_status()
    jwks = response.json().get("keys", [])
    header = jwt.get_unverified_header(id_token)
    jwk = next((key for key in jwks if key.get("kid") == header.get("kid")), None)
    if jwk is None:
        raise HTTPException(status_code=401, detail="Google signing key not found.")
    key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
    try:
        claims = jwt.decode(
            id_token,
            key=key,
            algorithms=["RS256"],
            audience=settings.google_client_id,
            issuer=GOOGLE_ISSUER,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
        )
    except jwt.PyJWTError as error:
        raise HTTPException(status_code=401, detail="Invalid Google identity token.") from error
    if not claims.get("email_verified") or not claims.get("email"):
        raise HTTPException(status_code=401, detail="Google email is not verified.")
    return claims


def upsert_google_user(claims: dict) -> User:
    google_sub = claims["sub"]
    email = claims["email"].lower()
    with SessionLocal.begin() as db:
        user = db.scalar(select(User).where(User.google_sub == google_sub))
        if user is None:
            email_user = db.scalar(select(User).where(User.email == email))
            if email_user is not None:
                raise HTTPException(
                    status_code=409,
                    detail="This email is already linked to another account.",
                )
            user = User(
                username=f"google_{google_sub}",
                google_sub=google_sub,
                email=email,
                full_name=claims.get("name"),
                picture_url=claims.get("picture"),
            )
            db.add(user)
        else:
            user.email = email
            user.full_name = claims.get("name")
            user.picture_url = claims.get("picture")
        db.flush()
        db.refresh(user)
        return user


def create_session_token(user: User) -> str:
    now = int(time.time())
    return jwt.encode(
        {"sub": str(user.id), "iat": now, "exp": now + SESSION_TTL_SECONDS},
        settings.session_secret,
        algorithm="HS256",
    )


def current_user(request: Request) -> User:
    token = request.cookies.get(settings.auth_cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required.")
    try:
        claims = jwt.decode(token, settings.session_secret, algorithms=["HS256"])
        user_id = int(claims["sub"])
    except (ValueError, KeyError, jwt.PyJWTError) as error:
        raise HTTPException(status_code=401, detail="Invalid or expired session.") from error
    with SessionLocal() as db:
        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="User account not found.")
        return user


def optional_current_user(request: Request) -> User | None:
    """Return the signed-in user when a session cookie is present."""
    if not request.cookies.get(settings.auth_cookie_name):
        return None
    return current_user(request)
