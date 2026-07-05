"""Review workflow store — the human-in-the-loop layer.

The Easy Read standard asks that simplified text be validated by people, ideally
the readers it is for. This is the persistence for that: a review holds the
source and the current output, a history of revisions, reviewer comments, and a
status. Backed by stdlib sqlite3 — no dependency, transactional, and it fits a
workflow store. A fresh connection per call keeps it safe under the threaded dev
server.

The store never runs the engine; callers pass a faithfulness snapshot if they
have one. Methods return plain JSON-ready dicts.
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

STATUSES = {"draft", "in_review", "approved", "rejected", "changes_requested"}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reviews (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  title TEXT NOT NULL,
  lang TEXT NOT NULL DEFAULT 'en',
  level TEXT NOT NULL DEFAULT 'plain',
  kind TEXT NOT NULL DEFAULT 'text',
  source TEXT NOT NULL,
  output TEXT NOT NULL,
  meta TEXT,
  status TEXT NOT NULL DEFAULT 'in_review',
  faithful INTEGER,
  created_by INTEGER,
  created_by_name TEXT
);
CREATE TABLE IF NOT EXISTS versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  review_id INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  output TEXT NOT NULL,
  note TEXT,
  faithful INTEGER
);
CREATE TABLE IF NOT EXISTS comments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  review_id INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  author TEXT NOT NULL,
  body TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _b(v):
    return None if v is None else (1 if v else 0)


def _ub(v):
    return None if v is None else bool(v)


def _default_db() -> Path:
    return Path(os.environ.get("CLARA_DB", Path.home() / ".clara" / "reviews.db"))


class ReviewStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else _default_db()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(_SCHEMA)
            # Migrate older DBs that predate attribution columns.
            for col, decl in (("created_by", "INTEGER"), ("created_by_name", "TEXT")):
                try:
                    c.execute(f"ALTER TABLE reviews ADD COLUMN {col} {decl}")
                except sqlite3.OperationalError:
                    pass

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

    def _summary(self, r) -> dict:
        return {
            "id": r["id"], "created_at": r["created_at"], "updated_at": r["updated_at"],
            "title": r["title"], "lang": r["lang"], "level": r["level"],
            "kind": r["kind"], "status": r["status"], "faithful": _ub(r["faithful"]),
            "created_by": r["created_by"], "created_by_name": r["created_by_name"],
        }

    def _full(self, r) -> dict:
        d = self._summary(r)
        d["source"] = r["source"]
        d["output"] = r["output"]
        d["meta"] = json.loads(r["meta"]) if r["meta"] else None
        return d

    def create_review(self, *, title, source, output, lang="en", level="plain",
                       kind="text", meta=None, faithful=None, status="in_review",
                       created_by=None, created_by_name=None) -> dict:
        if status not in STATUSES:
            raise ValueError(f"Unknown status '{status}'.")
        now = _now()
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO reviews(created_at,updated_at,title,lang,level,kind,source,"
                "output,meta,status,faithful,created_by,created_by_name) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (now, now, title or "Untitled", lang, level, kind, source, output,
                 json.dumps(meta) if meta is not None else None, status, _b(faithful),
                 created_by, created_by_name),
            )
            rid = cur.lastrowid
            c.execute(
                "INSERT INTO versions(review_id,created_at,output,note,faithful) VALUES(?,?,?,?,?)",
                (rid, now, output, "initial", _b(faithful)),
            )
        return self.get_review(rid)

    def list_reviews(self, status=None) -> list[dict]:
        q = ("SELECT id,created_at,updated_at,title,lang,level,kind,status,faithful,"
             "created_by,created_by_name FROM reviews")
        args: tuple = ()
        if status:
            q += " WHERE status=?"
            args = (status,)
        q += " ORDER BY updated_at DESC, id DESC"
        with self._conn() as c:
            return [self._summary(r) for r in c.execute(q, args).fetchall()]

    def get_review(self, review_id) -> dict | None:
        with self._conn() as c:
            r = c.execute("SELECT * FROM reviews WHERE id=?", (review_id,)).fetchone()
            if not r:
                return None
            versions = c.execute(
                "SELECT id,created_at,output,note,faithful FROM versions "
                "WHERE review_id=? ORDER BY id", (review_id,)).fetchall()
            comments = c.execute(
                "SELECT id,created_at,author,body FROM comments "
                "WHERE review_id=? ORDER BY id", (review_id,)).fetchall()
        d = self._full(r)
        d["versions"] = [
            {"id": v["id"], "created_at": v["created_at"], "output": v["output"],
             "note": v["note"], "faithful": _ub(v["faithful"])}
            for v in versions
        ]
        d["comments"] = [dict(x) for x in comments]
        return d

    def add_comment(self, review_id, author, body) -> dict | None:
        now = _now()
        with self._conn() as c:
            if not c.execute("SELECT 1 FROM reviews WHERE id=?", (review_id,)).fetchone():
                return None
            c.execute("INSERT INTO comments(review_id,created_at,author,body) VALUES(?,?,?,?)",
                      (review_id, now, (author or "anon").strip() or "anon", body))
            c.execute("UPDATE reviews SET updated_at=? WHERE id=?", (now, review_id))
        return self.get_review(review_id)

    def set_status(self, review_id, status) -> dict | None:
        if status not in STATUSES:
            raise ValueError(f"Unknown status '{status}'.")
        now = _now()
        with self._conn() as c:
            cur = c.execute("UPDATE reviews SET status=?, updated_at=? WHERE id=?",
                            (status, now, review_id))
            if cur.rowcount == 0:
                return None
        return self.get_review(review_id)

    def add_revision(self, review_id, output, note=None, faithful=None) -> dict | None:
        now = _now()
        with self._conn() as c:
            if not c.execute("SELECT 1 FROM reviews WHERE id=?", (review_id,)).fetchone():
                return None
            c.execute(
                "INSERT INTO versions(review_id,created_at,output,note,faithful) VALUES(?,?,?,?,?)",
                (review_id, now, output, note, _b(faithful)),
            )
            c.execute("UPDATE reviews SET output=?, faithful=?, updated_at=? WHERE id=?",
                      (output, _b(faithful), now, review_id))
        return self.get_review(review_id)

    def delete_review(self, review_id) -> bool:
        with self._conn() as c:
            c.execute("DELETE FROM versions WHERE review_id=?", (review_id,))
            c.execute("DELETE FROM comments WHERE review_id=?", (review_id,))
            cur = c.execute("DELETE FROM reviews WHERE id=?", (review_id,))
        return cur.rowcount > 0
