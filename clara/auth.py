"""Authentication and users for multi-user review.

stdlib only, in the project's spirit: passwords are hashed with pbkdf2_hmac
(salt + many iterations), sessions are opaque tokens in the same sqlite DB as
reviews. Off by default — set CLARA_AUTH=1 to require a login for the review
workflow. The engine endpoints (simplify/verify/…) never require auth.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

_ITERATIONS = 200_000
ROLES = {"admin", "reviewer"}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'reviewer',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);
"""


def auth_enabled() -> bool:
    return os.environ.get("CLARA_AUTH", "").strip().lower() in ("1", "true", "yes", "on")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _algo, iters, salt, hexhash = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iters))
        return hmac.compare_digest(dk.hex(), hexhash)
    except Exception:
        return False


def bearer_token(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def _default_db() -> Path:
    return Path(os.environ.get("CLARA_DB", Path.home() / ".clara" / "reviews.db"))


class AuthStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else _default_db()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(_SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=5000")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _public(row) -> dict:
        return {"id": row["id"], "username": row["username"], "role": row["role"],
                "created_at": row["created_at"]}

    def count_users(self) -> int:
        with self._conn() as c:
            return c.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]

    def create_user(self, username: str, password: str, role: str | None = None) -> dict:
        username = (username or "").strip()
        if not username or not password:
            raise ValueError("username and password are required")
        if role is None:
            role = "admin" if self.count_users() == 0 else "reviewer"  # first user bootstraps admin
        if role not in ROLES:
            raise ValueError(f"Unknown role '{role}'. Options: {', '.join(sorted(ROLES))}")
        now = _iso(_now())
        try:
            with self._conn() as c:
                cur = c.execute(
                    "INSERT INTO users(username,password,role,created_at) VALUES(?,?,?,?)",
                    (username, hash_password(password), role, now),
                )
                uid = cur.lastrowid
        except sqlite3.IntegrityError:
            raise ValueError(f"User '{username}' already exists.")
        return {"id": uid, "username": username, "role": role, "created_at": now}

    def authenticate(self, username: str, password: str) -> dict | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if row and verify_password(password, row["password"]):
            return self._public(row)
        return None

    def login(self, username: str, password: str, ttl_days: int = 30) -> dict | None:
        user = self.authenticate(username, password)
        if not user:
            return None
        token = secrets.token_urlsafe(32)
        now = _now()
        with self._conn() as c:
            c.execute(
                "INSERT INTO sessions(token,user_id,created_at,expires_at) VALUES(?,?,?,?)",
                (token, user["id"], _iso(now), _iso(now + timedelta(days=ttl_days))),
            )
        return {"token": token, "user": user}

    def user_for_token(self, token: str | None) -> dict | None:
        if not token:
            return None
        with self._conn() as c:
            row = c.execute(
                "SELECT u.*, s.expires_at AS exp FROM sessions s "
                "JOIN users u ON u.id = s.user_id WHERE s.token=?",
                (token,),
            ).fetchone()
        if not row:
            return None
        if _iso(_now()) > row["exp"]:
            self.logout(token)
            return None
        return self._public(row)

    def logout(self, token: str | None) -> None:
        if token:
            with self._conn() as c:
                c.execute("DELETE FROM sessions WHERE token=?", (token,))

    def list_users(self) -> list[dict]:
        with self._conn() as c:
            return [self._public(r) for r in c.execute("SELECT * FROM users ORDER BY id").fetchall()]
