"""Supabase JWT authentication dependency.

Verifies JWT tokens from the ``Authorization: Bearer <token>`` header
using the Supabase project's JWT secret (derived from ``supabase_anon_key``).
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError

_bearer_scheme = HTTPBearer(auto_error=False)


def _decode_jwt(token: str, secret: str) -> dict:
    """Decode and verify a Supabase JWT token."""
    try:
        import jwt  # PyJWT
    except ImportError as exc:
        raise RuntimeError('PyJWT is required for JWT authentication') from exc

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=['HS256'],
            options={
                'verify_aud': False,
                'verify_iss': False,
            },
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError('Token has expired')
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError(f'Invalid token: {exc}')


async def require_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    settings: Settings = Depends(lambda: get_settings()),
) -> dict:
    """FastAPI dependency that enforces Supabase JWT auth.

    Extracts the bearer token, verifies it against the Supabase JWT secret,
    and returns the decoded payload. Raises 401 on failure.

    In dev mode (``APP_ENV=dev``), auth is optional and returns a stub payload
    when no token is provided.
    """
    if settings.app_env == 'dev' and credentials is None:
        # Allow unauthenticated access in dev mode
        return {'sub': 'dev-user', 'role': 'anon', 'dev_mode': True}

    if credentials is None:
        raise HTTPException(status_code=401, detail='Missing authorization header')

    secret = settings.supabase_anon_key
    if not secret:
        raise HTTPException(status_code=500, detail='Auth not configured (missing SUPABASE_ANON_KEY)')

    try:
        payload = _decode_jwt(credentials.credentials, secret)
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    request.state.user = payload
    return payload
