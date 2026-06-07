from __future__ import annotations

import hmac

import bcrypt
from fastapi import Request

from redclaw.config import Settings


SESSION_COOKIE = "redclaw_session"


def verify_password(candidate: str, configured: str) -> bool:
    if configured.startswith("$2"):
        return bcrypt.checkpw(candidate.encode("utf-8"), configured.encode("utf-8"))
    return hmac.compare_digest(candidate, configured)


def session_token(settings: Settings) -> str:
    return f"redcrafter:{settings.session_secret}"


def is_authenticated(request: Request, settings: Settings) -> bool:
    token = request.cookies.get(SESSION_COOKIE, "")
    return hmac.compare_digest(token, session_token(settings))
