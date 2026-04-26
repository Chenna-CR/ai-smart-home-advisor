from typing import Dict, Optional
from uuid import uuid4

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from .config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    SESSION_COOKIE_SECURE,
)
from .database import upsert_user

GUEST_COOKIE_NAME = "guest_id"


oauth = OAuth()
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


auth_router = APIRouter(tags=["auth"])


def _set_guest_cookie(response: RedirectResponse, guest_id: str) -> None:
    response.set_cookie(
        key=GUEST_COOKIE_NAME,
        value=guest_id,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )


def ensure_guest_id(request: Request, response: Optional[RedirectResponse] = None) -> str:
    existing = request.cookies.get(GUEST_COOKIE_NAME)
    if existing:
        return existing

    guest_id = str(uuid4())
    if response is not None:
        _set_guest_cookie(response, guest_id)
    return guest_id


def get_active_identity(request: Request) -> Dict[str, Optional[str]]:
    state_guest_id = getattr(getattr(request, "state", object()), "guest_id", None)
    cookie_guest_id = request.cookies.get(GUEST_COOKIE_NAME)
    effective_guest_id = state_guest_id or cookie_guest_id

    user = request.session.get("user") if hasattr(request, "session") else None
    if user and user.get("email"):
        return {
            "is_authenticated": True,
            "user_id": user.get("email"),
            "guest_id": effective_guest_id,
            "name": user.get("name"),
            "email": user.get("email"),
            "profile_pic": user.get("picture"),
        }

    return {
        "is_authenticated": False,
        "user_id": None,
        "guest_id": effective_guest_id,
        "name": "Guest User",
        "email": None,
        "profile_pic": None,
    }


def ensure_identity(request: Request) -> Dict[str, Optional[str]]:
    identity = get_active_identity(request)
    if identity["is_authenticated"]:
        return identity

    guest_id = identity.get("guest_id") or str(uuid4())
    return {
        **identity,
        "guest_id": guest_id,
    }


@auth_router.get("/login")
async def login(request: Request):
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")

    redirect_uri = GOOGLE_REDIRECT_URI or str(request.url_for("auth_callback"))
    google = oauth.create_client("google")
    if google is None:
        raise HTTPException(status_code=503, detail="Google OAuth client is unavailable")
    return await google.authorize_redirect(request, redirect_uri)


@auth_router.get("/auth/callback")
async def auth_callback(request: Request):
    google = oauth.create_client("google")
    if google is None:
        raise HTTPException(status_code=503, detail="Google OAuth client is unavailable")

    token = await google.authorize_access_token(request)
    user_info = token.get("userinfo")
    if not user_info:
        user_info = await google.parse_id_token(request, token)

    if not user_info or not user_info.get("email"):
        raise HTTPException(status_code=400, detail="Google authentication failed")

    profile = {
        "email": user_info.get("email"),
        "name": user_info.get("name") or "User",
        "picture": user_info.get("picture") or "",
    }
    request.session["user"] = profile
    request.session["google_token"] = {
        "access_token": token.get("access_token"),
        "id_token": token.get("id_token"),
    }

    upsert_user(profile["email"], profile["name"], profile["picture"])

    response = RedirectResponse(url="/", status_code=302)
    if request.cookies.get(GUEST_COOKIE_NAME):
        response.delete_cookie(GUEST_COOKIE_NAME)
    return response


@auth_router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    response = RedirectResponse(url="/", status_code=302)
    if not request.cookies.get(GUEST_COOKIE_NAME):
        _set_guest_cookie(response, str(uuid4()))
    return response


@auth_router.get("/auth/me")
async def auth_me(request: Request):
    identity = ensure_identity(request)
    logged_in = bool(identity["is_authenticated"])
    user_payload = None
    if logged_in:
        user_payload = {
            "name": identity.get("name"),
            "email": identity.get("email"),
            "profile_pic": identity.get("profile_pic"),
        }

    return {
        "logged_in": logged_in,
        "is_authenticated": logged_in,
        "user": user_payload,
        "guest_id": identity.get("guest_id"),
    }
