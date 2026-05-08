import re
from typing import Iterable

from fastapi import HTTPException, Request
from passlib.context import CryptContext
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

import db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

PROMPT_INJECTION_PATTERNS = (
    "ignore previous instructions",
    "ignore all previous",
    "system prompt",
    "developer message",
    "reveal your prompt",
    "override instructions",
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return True
    return pwd_context.verify(password, password_hash)


def clamp_text(value: str, field: str, min_len: int, max_len: int) -> str:
    text = value.strip()
    if not min_len <= len(text) <= max_len:
        raise HTTPException(400, f"{field} must be between {min_len} and {max_len} characters")
    return text


def validate_username(username: str) -> str:
    username = clamp_text(username, "username", 2, 40)
    if not re.fullmatch(r"[A-Za-z0-9_. -]+", username):
        raise HTTPException(400, "username contains unsupported characters")
    return username


def reject_prompt_injection(text: str) -> None:
    lowered = text.lower()
    if any(pattern in lowered for pattern in PROMPT_INJECTION_PATTERNS):
        raise HTTPException(400, "official actions cannot contain prompt-control instructions")


async def require_member(campaign_id: str, username: str, roles: Iterable[str] | None = None):
    role_filter = tuple(roles or ())
    player = await db.fetchrow(
        """
        SELECT p.id, p.username, cm.role
        FROM players p
        JOIN campaign_members cm ON cm.player_id = p.id
        WHERE cm.campaign_id = $1::uuid AND p.username = $2
        """,
        campaign_id,
        username,
    )
    if not player:
        raise HTTPException(403, "campaign membership required")
    if role_filter and player["role"] not in role_filter:
        raise HTTPException(403, "campaign role is not allowed for this action")
    return player


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; connect-src 'self' ws: wss:; "
            "script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; object-src 'none'; base-uri 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        return response
