"""Email + password auth with cookie-persistent sessions.

Session token lifecycle:
  1. On signup/login → create a row in `sessions` table → set cookie + ss
  2. On every page load → read cookie → look up token → restore ss
  3. On logout → delete session row + clear cookie + clear ss

Survives browser refresh, browser restart, and (within token TTL) re-visits.
"""
from __future__ import annotations

import re
from typing import TypedDict

import bcrypt
import streamlit as st

from . import db

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Cookie + session_state keys
_COOKIE_NAME = "meta_ads_session"
_SS_USER_ID = "auth_user_id"
_SS_TOKEN = "auth_token"


class AuthError(Exception):
    pass


class CurrentUser(TypedDict):
    id: int
    email: str
    currency: str
    tier: str
    client_limit: int
    team_seats: int
    is_admin: bool


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ---------- Cookie controller (lazy + idempotent) ----------

def _cookies():
    """Return a CookieController, or None when Streamlit context isn't ready
    (e.g. during unit tests). Lazy-import so non-Streamlit callers still work."""
    try:
        from streamlit_cookies_controller import CookieController  # type: ignore[import-not-found]
    except ImportError:
        return None
    try:
        return CookieController(key="meta_ads_cookies")
    except Exception:
        return None


def _read_cookie_token() -> str | None:
    c = _cookies()
    if c is None:
        return None
    try:
        return c.get(_COOKIE_NAME)
    except Exception:
        return None


def _write_cookie_token(token: str) -> None:
    c = _cookies()
    if c is None:
        return
    try:
        c.set(_COOKIE_NAME, token, max_age=30 * 24 * 3600)   # 30 days
    except Exception:
        pass


def _delete_cookie_token() -> None:
    c = _cookies()
    if c is None:
        return
    try:
        c.remove(_COOKIE_NAME)
    except Exception:
        pass


# ---------- Public API ----------

def signup(email: str, password: str, currency: str = "INR") -> int:
    email = email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise AuthError("Enter a valid email address.")
    if len(password) < 8:
        raise AuthError("Password must be at least 8 characters.")
    if currency not in ("INR", "USD"):
        raise AuthError("Currency must be INR or USD.")
    if db.find_user_by_email(email):
        raise AuthError("An account with this email already exists.")
    return db.create_user(email=email, password_hash=_hash(password), currency=currency, trial_days=2)


def login(email: str, password: str) -> dict:
    email = email.strip().lower()
    user = db.find_user_by_email(email)
    if not user or not _verify(password, user["password_hash"]):
        raise AuthError("Incorrect email or password.")
    return user


def set_session(user_id: int) -> None:
    """Create a fresh session token, store in DB + cookie + ss."""
    token = db.create_session(user_id)
    st.session_state[_SS_USER_ID] = user_id
    st.session_state[_SS_TOKEN] = token
    _write_cookie_token(token)


def clear_session() -> None:
    """Tear down the session — DB row, cookie, ss."""
    token = st.session_state.get(_SS_TOKEN) or _read_cookie_token()
    if token:
        try:
            db.delete_session(token)
        except Exception:
            pass
    for key in (_SS_USER_ID, _SS_TOKEN):
        if key in st.session_state:
            del st.session_state[key]
    _delete_cookie_token()


def _restore_from_cookie() -> int | None:
    """Try to rebuild ss from a cookie token. Returns user_id if successful."""
    token = _read_cookie_token()
    if not token:
        return None
    row = db.find_session(token)
    if not row:
        return None
    user_id = int(row["user_id"])
    # Make sure the user still exists (could have been deleted)
    if not db.find_user(user_id):
        db.delete_session(token)
        return None
    st.session_state[_SS_USER_ID] = user_id
    st.session_state[_SS_TOKEN] = token
    return user_id


def current_user() -> CurrentUser | None:
    """Return the currently logged-in user, restoring from cookie if needed."""
    user_id = st.session_state.get(_SS_USER_ID)
    if not user_id:
        user_id = _restore_from_cookie()
    if not user_id:
        return None
    u = db.find_user(user_id)
    if not u:
        clear_session()
        return None
    return CurrentUser(
        id=u["id"],
        email=u["email"],
        currency=u["currency"],
        tier=u["tier"],
        client_limit=u["client_limit"],
        team_seats=u["team_seats"],
        is_admin=bool(u["is_admin"]),
    )
