"""SQLite layer (local) / Turso layer (production) — same API both ways.

The adapter chooses backend by env:
  • TURSO_DATABASE_URL set → libsql HTTP client to cloud
  • Otherwise              → local file at Meta_Ads/data/meta_ads.db

The rest of the codebase calls high-level functions (create_user,
find_user_by_email, …) that internally use _execute / _fetchone / _fetchall
helpers — those handle the two backends transparently.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "meta_ads.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _is_turso() -> bool:
    return bool(os.environ.get("TURSO_DATABASE_URL"))


_turso_client = None


def _turso():
    """Lazy-init the libsql HTTP client. Single global instance."""
    global _turso_client
    if _turso_client is None:
        from libsql_client import create_client_sync  # type: ignore[import-not-found]
        _turso_client = create_client_sync(
            url=os.environ["TURSO_DATABASE_URL"],
            auth_token=os.environ.get("TURSO_AUTH_TOKEN", ""),
        )
    return _turso_client


# ---------- Unified execute helpers ----------

def _params_tuple(params: tuple | list | None) -> tuple:
    if params is None:
        return ()
    return tuple(params)


def _execute(sql: str, params: tuple | list | None = None) -> dict:
    """Run a single statement. Returns {"lastrowid": int|None, "rowcount": int}."""
    params = _params_tuple(params)
    if _is_turso():
        client = _turso()
        result = client.execute(sql, params)
        return {
            "lastrowid": getattr(result, "last_insert_rowid", None),
            "rowcount": getattr(result, "rows_affected", 0),
        }
    # Local sqlite
    conn = sqlite3.connect(str(DB_PATH))
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return {"lastrowid": cur.lastrowid, "rowcount": cur.rowcount}
    finally:
        conn.close()


def _fetchone(sql: str, params: tuple | list | None = None) -> dict | None:
    rows = _fetchall(sql, params)
    return rows[0] if rows else None


def _fetchall(sql: str, params: tuple | list | None = None) -> list[dict]:
    params = _params_tuple(params)
    if _is_turso():
        client = _turso()
        result = client.execute(sql, params)
        cols = list(result.columns)
        return [dict(zip(cols, row)) for row in result.rows]
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def _executescript(sql: str) -> None:
    """Run multi-statement DDL. Splits on `;` and executes each non-empty piece."""
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    for stmt in statements:
        _execute(stmt)


# ---------- Schema ----------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    email           TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    currency        TEXT NOT NULL DEFAULT 'INR',
    tier            TEXT NOT NULL DEFAULT 'starter',
    client_limit    INTEGER NOT NULL DEFAULT 1,
    team_seats      INTEGER NOT NULL DEFAULT 1,
    is_admin        INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL,
    trial_ends_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS subscriptions (
    user_id                  INTEGER PRIMARY KEY,
    status                   TEXT NOT NULL DEFAULT 'trialing',
    provider                 TEXT,
    razorpay_subscription_id TEXT,
    razorpay_customer_id     TEXT,
    current_period_end       TEXT,
    paused_campaign_ids      TEXT DEFAULT '[]',
    last_polled_at           TEXT
);

CREATE TABLE IF NOT EXISTS clients (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    ad_account_id   TEXT NOT NULL,
    page_id         TEXT,
    business_name   TEXT,
    created_at      TEXT NOT NULL,
    UNIQUE(user_id, ad_account_id)
);

CREATE TABLE IF NOT EXISTS sessions (
    token       TEXT PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    created_at  TEXT NOT NULL,
    expires_at  TEXT NOT NULL
);
"""


def _init():
    _executescript(_SCHEMA)


_init()


# ---------- Backwards-compat conn() — used by older test scripts ----------

@contextmanager
def conn():
    """Legacy SQLite-only context manager. Use _execute/_fetchall for new code."""
    if _is_turso():
        raise RuntimeError(
            "conn() context manager is SQLite-only. "
            "Use _execute / _fetchall helpers when TURSO_DATABASE_URL is set."
        )
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    try:
        yield c
        c.commit()
    finally:
        c.close()


# ---------- Helpers ----------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def days_from_now(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


# ---------- Users ----------

def create_user(email: str, password_hash: str, currency: str = "INR", trial_days: int = 2) -> int:
    res = _execute(
        """INSERT INTO users (email, password_hash, currency, created_at, trial_ends_at)
           VALUES (?, ?, ?, ?, ?)""",
        (email, password_hash, currency, now_iso(), days_from_now(trial_days)),
    )
    user_id = res["lastrowid"]
    _execute(
        "INSERT INTO subscriptions (user_id, status) VALUES (?, 'trialing')",
        (user_id,),
    )
    return user_id


def find_user_by_email(email: str) -> dict | None:
    return _fetchone("SELECT * FROM users WHERE email = ?", (email,))


def find_user(user_id: int) -> dict | None:
    return _fetchone("SELECT * FROM users WHERE id = ?", (user_id,))


def list_users() -> list[dict]:
    return _fetchall(
        """SELECT u.*, s.status AS sub_status, s.current_period_end
           FROM users u LEFT JOIN subscriptions s ON s.user_id = u.id
           ORDER BY u.created_at DESC"""
    )


def update_user_tier(user_id: int, tier: str, client_limit: int, team_seats: int) -> None:
    _execute(
        "UPDATE users SET tier = ?, client_limit = ?, team_seats = ? WHERE id = ?",
        (tier, client_limit, team_seats, user_id),
    )


def make_admin(user_id: int) -> None:
    _execute("UPDATE users SET is_admin = 1 WHERE id = ?", (user_id,))


# ---------- Subscriptions ----------

def get_subscription(user_id: int) -> dict | None:
    row = _fetchone("SELECT * FROM subscriptions WHERE user_id = ?", (user_id,))
    if not row:
        return None
    row["paused_campaign_ids"] = json.loads(row.get("paused_campaign_ids") or "[]")
    return row


def set_subscription_status(user_id: int, status: str, period_end: str | None = None) -> None:
    if period_end:
        _execute(
            """UPDATE subscriptions
               SET status = ?, current_period_end = ?, last_polled_at = ?
               WHERE user_id = ?""",
            (status, period_end, now_iso(), user_id),
        )
    else:
        _execute(
            "UPDATE subscriptions SET status = ?, last_polled_at = ? WHERE user_id = ?",
            (status, now_iso(), user_id),
        )


def set_razorpay_ids(user_id: int, subscription_id: str | None, customer_id: str | None) -> None:
    _execute(
        """UPDATE subscriptions
           SET razorpay_subscription_id = ?, razorpay_customer_id = ?, provider = 'razorpay'
           WHERE user_id = ?""",
        (subscription_id, customer_id, user_id),
    )


def set_paused_campaigns(user_id: int, campaign_ids: list[str]) -> None:
    _execute(
        "UPDATE subscriptions SET paused_campaign_ids = ? WHERE user_id = ?",
        (json.dumps(campaign_ids), user_id),
    )


def extend_subscription(user_id: int, days: int = 30) -> None:
    end = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    _execute(
        """UPDATE subscriptions
           SET status = 'active', current_period_end = ?,
               provider = COALESCE(provider, 'manual')
           WHERE user_id = ?""",
        (end, user_id),
    )


# ---------- Clients ----------

def add_client(user_id: int, ad_account_id: str, page_id: str = "", business_name: str = "") -> int:
    res = _execute(
        """INSERT INTO clients (user_id, ad_account_id, page_id, business_name, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, ad_account_id, page_id, business_name, now_iso()),
    )
    return res["lastrowid"]


def list_clients(user_id: int) -> list[dict]:
    return _fetchall("SELECT * FROM clients WHERE user_id = ? ORDER BY created_at", (user_id,))


def client_count(user_id: int) -> int:
    row = _fetchone("SELECT COUNT(*) AS n FROM clients WHERE user_id = ?", (user_id,))
    return int(row["n"]) if row else 0


def remove_client(client_id: int, user_id: int) -> None:
    _execute("DELETE FROM clients WHERE id = ? AND user_id = ?", (client_id, user_id))


# ---------- Sessions (cookie-token persistence) ----------

def create_session(user_id: int, days_valid: int = 30) -> str:
    """Issue a new session token. Returns the token to store in a cookie."""
    token = uuid.uuid4().hex
    _execute(
        "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (token, user_id, now_iso(), days_from_now(days_valid)),
    )
    return token


def find_session(token: str) -> dict | None:
    row = _fetchone(
        "SELECT * FROM sessions WHERE token = ?", (token,)
    )
    if not row:
        return None
    expires_at = parse_iso(row.get("expires_at"))
    if expires_at and datetime.now(timezone.utc) > expires_at:
        delete_session(token)
        return None
    return row


def delete_session(token: str) -> None:
    _execute("DELETE FROM sessions WHERE token = ?", (token,))


def delete_user_sessions(user_id: int) -> None:
    _execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
