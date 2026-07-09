#!/usr/bin/env python3
"""Zero-dependency dev server for the Clara reference UI.

Serves web/index.html and handles POST /simplify and /verify by calling the
engine directly — no third-party web framework, just stock Python.

    py web/serve.py                 # http://localhost:8000
    py web/serve.py --port 9000

The "Check a rewrite" mode (/verify) needs no LLM and works fully offline.
"Simplify" uses whatever provider is set (default 'mock' echoes the text).
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make 'clara' importable

from clara.auth import (  # noqa: E402
    AuthStore,
    RateLimitedError,
    auth_enabled,
    bearer_token,
    can_approve,
    is_admin,
)
from clara.board import board  # noqa: E402
from clara.easyread import ask, easy_read  # noqa: E402
from clara.export import document_html, document_pdf  # noqa: E402
from clara.i18n import ui_strings  # noqa: E402
from clara.ingest import from_url, ingest_bytes  # noqa: E402
from clara.llm import get_check_provider, get_provider  # noqa: E402
from clara.pictograms import get_symbol_provider  # noqa: E402
from clara.pipeline import simplify_structured, simplify_text  # noqa: E402
from clara.readability import analyze  # noqa: E402
from clara.review import ReviewStore  # noqa: E402
from clara.semantic import semantic_check  # noqa: E402
from clara.serialize import (  # noqa: E402
    easyread_dict,
    faithfulness_dict,
    readability_dict,
    result_dict,
    semantic_dict,
    structured_dict,
)
from clara.structure import block_dict, block_from_dict  # noqa: E402
from clara.verify import verify  # noqa: E402

INDEX = Path(__file__).resolve().parent / "index.html"
_reviews = ReviewStore()
_auth = AuthStore()


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, body: bytes, content_type: str, filename: str):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n).decode("utf-8")) if n else {}

    def _require_user(self):
        """Return (user_or_None, ok). ok=False means a 401 was already sent."""
        if not auth_enabled():
            return None, True
        user = _auth.user_for_token(bearer_token(self.headers.get("Authorization")))
        if not user:
            self._send_json({"error": "Authentication required"}, 401)
            return None, False
        return user, True

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = INDEX.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/health":
            self._send_json({"status": "ok"})
        elif self.path == "/i18n":
            self._send_json(ui_strings())
        elif self.path.split("?", 1)[0] == "/board":
            q = parse_qs(urlparse(self.path).query)
            self._send_json(board(lang=(q.get("lang") or ["en"])[0],
                                  symbols=(q.get("symbols") or [None])[0]))
        elif self.path == "/auth/status":
            user = _auth.user_for_token(bearer_token(self.headers.get("Authorization"))) if auth_enabled() else None
            self._send_json({"enabled": auth_enabled(), "users": _auth.count_users(), "user": user})
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        try:
            data = self._read_json()
            if self.path == "/simplify":
                provider = get_provider(data.get("provider"))
                res = simplify_text(
                    data.get("text", ""),
                    level=data.get("level", "plain"),
                    provider=provider,
                    grade=data.get("grade"),
                    lang=data.get("lang", "en"),
                )
                self._send_json(result_dict(res))
            elif self.path == "/simplify_structured":
                provider = get_provider(data.get("provider"))
                blocks = [block_from_dict(b) for b in data.get("blocks", [])]
                res = simplify_structured(
                    blocks,
                    level=data.get("level", "plain"),
                    provider=provider,
                    grade=data.get("grade"),
                    lang=data.get("lang", "en"),
                )
                self._send_json(structured_dict(res))
            elif self.path == "/verify":
                source, output = data.get("source", ""), data.get("output", "")
                lang = data.get("lang", "en")
                self._send_json({
                    "faithfulness": faithfulness_dict(verify(source, output, lang=lang)),
                    "source_readability": readability_dict(analyze(source, lang)),
                    "output_readability": readability_dict(analyze(output, lang)),
                })
            elif self.path == "/easyread":
                provider = get_provider(data.get("provider"))
                res = easy_read(data.get("text", ""), provider=provider,
                                lang=data.get("lang", "en"), symbols=data.get("symbols"))
                self._send_json(easyread_dict(res))
            elif self.path == "/ask":
                provider = get_provider(data.get("provider"))
                res = ask(data.get("text", ""), provider=provider,
                          lang=data.get("lang", "en"), symbols=data.get("symbols"))
                out = easyread_dict(res)
                out["question"] = data.get("text", "")
                self._send_json(out)
            elif self.path == "/pictograms/search":
                sp = get_symbol_provider(data.get("symbols"))
                hits = sp.search(data.get("keyword", ""), lang=data.get("lang", "en"),
                                 limit=int(data.get("limit", 12)))
                self._send_json({"provider": sp.name,
                                 "results": [{"id": s.id, "keyword": s.label, "image_url": s.image_url} for s in hits]})
            elif self.path == "/semantic":
                provider = get_check_provider(data.get("provider"))  # independent grader by default
                rep = semantic_check(data.get("source", ""), data.get("output", ""),
                                     provider=provider, lang=data.get("lang", "en"))
                self._send_json(semantic_dict(rep))
            elif self.path == "/ingest":
                try:
                    if data.get("url"):
                        res = from_url(data["url"])
                    elif data.get("content_b64") is not None:
                        raw = base64.b64decode(data["content_b64"])
                        res = ingest_bytes(data.get("filename", "file.txt"), raw,
                                           ocr=data.get("ocr", "auto"))
                    else:
                        self._send_json({"error": "Provide a url or a file."}, 400)
                        return
                except RuntimeError as e:
                    self._send_json({"error": str(e)}, 501)
                    return
                self._send_json({"text": res.text, "title": res.title, "kind": res.kind,
                                 "ocr_applied": res.ocr_applied,
                                 "blocks": [block_dict(b) for b in res.blocks]})
            elif self.path == "/auth/register":
                if not auth_enabled():
                    self._send_json({"error": "Authentication is not enabled."}, 400)
                elif _auth.count_users() > 0:
                    self._send_json({"error": "Registration is closed. Ask an admin to add your account."}, 403)
                else:
                    try:
                        _auth.create_user(data.get("username", ""), data.get("password", ""))
                    except ValueError as e:
                        self._send_json({"error": str(e)}, 400)
                    else:
                        self._send_json(_auth.login(data.get("username", ""), data.get("password", "")))
            elif self.path == "/auth/login":
                if not auth_enabled():
                    self._send_json({"error": "Authentication is not enabled."}, 400)
                else:
                    try:
                        result = _auth.login(data.get("username", ""), data.get("password", ""))
                    except RateLimitedError as e:
                        self._send_json({"error": str(e)}, 429)
                    else:
                        if result:
                            self._send_json(result)
                        else:
                            self._send_json({"error": "Invalid username or password."}, 401)
            elif self.path == "/auth/users":
                user, ok = self._require_user()
                if not ok:
                    return
                if auth_enabled() and not is_admin(user):
                    self._send_json({"error": "Admin only."}, 403)
                else:
                    self._send_json({"users": _auth.list_users()})
            elif self.path == "/auth/logout":
                _auth.logout(bearer_token(self.headers.get("Authorization")))
                self._send_json({"ok": True})
            elif self.path == "/reviews/create":
                user, ok = self._require_user()
                if not ok:
                    return
                try:
                    self._send_json(_reviews.create_review(
                        title=data.get("title", "Untitled"), source=data.get("source", ""),
                        output=data.get("output", ""), lang=data.get("lang", "en"),
                        level=data.get("level", "plain"), kind=data.get("kind", "text"),
                        meta=data.get("meta"), faithful=data.get("faithful"),
                        status=data.get("status", "in_review"),
                        created_by=user["id"] if user else None,
                        created_by_name=user["username"] if user else data.get("created_by_name")))
                except ValueError as e:
                    self._send_json({"error": str(e)}, 400)
            elif self.path == "/reviews/list":
                user, ok = self._require_user()
                if not ok:
                    return
                self._send_json({"reviews": _reviews.list_reviews(status=data.get("status"))})
            elif self.path == "/reviews/get":
                user, ok = self._require_user()
                if not ok:
                    return
                r = _reviews.get_review(data.get("id"))
                self._send_json(r) if r else self._send_json({"error": "not found"}, 404)
            elif self.path == "/reviews/comment":
                user, ok = self._require_user()
                if not ok:
                    return
                author = user["username"] if user else data.get("author")
                r = _reviews.add_comment(data.get("id"), author, data.get("body", ""))
                self._send_json(r) if r else self._send_json({"error": "not found"}, 404)
            elif self.path == "/reviews/status":
                user, ok = self._require_user()
                if not ok:
                    return
                current = _reviews.get_review(data.get("id"))
                signoff = data.get("status") in ("approved", "rejected")
                if not current:
                    self._send_json({"error": "not found"}, 404)
                elif signoff and not can_approve(user, current.get("assignee_id")):
                    self._send_json({"error": "Only an admin or the assigned validator can approve or reject."}, 403)
                else:
                    try:
                        r = _reviews.set_status(data.get("id"), data.get("status"))
                    except ValueError as e:
                        self._send_json({"error": str(e)}, 400)
                    else:
                        self._send_json(r) if r else self._send_json({"error": "not found"}, 404)
            elif self.path == "/reviews/assign":
                user, ok = self._require_user()
                if not ok:
                    return
                if auth_enabled() and not is_admin(user):
                    self._send_json({"error": "Only an admin can assign reviews."}, 403)
                else:
                    r = _reviews.assign_review(data.get("id"), data.get("assignee_id"), data.get("assignee_name"))
                    self._send_json(r) if r else self._send_json({"error": "not found"}, 404)
            elif self.path == "/reviews/revision":
                user, ok = self._require_user()
                if not ok:
                    return
                r = _reviews.add_revision(data.get("id"), data.get("output", ""),
                                          note=data.get("note"), faithful=data.get("faithful"))
                self._send_json(r) if r else self._send_json({"error": "not found"}, 404)
            elif self.path == "/export":
                doc = document_html(title=data.get("title", "Plain-language document"),
                                    lang=data.get("lang", "en"), kind=data.get("kind", "text"),
                                    text=data.get("text"), lines=data.get("lines"),
                                    blocks=data.get("blocks"),
                                    footer=data.get("footer"),
                                    embed_images=data.get("embed_images", False))
                if data.get("format") == "pdf":
                    try:
                        self._send_bytes(document_pdf(doc), "application/pdf", "clara.pdf")
                    except RuntimeError as e:
                        self._send_json({"error": str(e)}, 501)
                else:
                    self._send_bytes(doc.encode("utf-8"), "text/html; charset=utf-8", "clara.html")
            else:
                self._send_json({"error": "not found"}, 404)
        except Exception as e:  # keep the dev server up; surface the message to the UI
            self._send_json({"error": f"{type(e).__name__}: {e}"}, 400)

    def log_message(self, *args):  # quieter console
        pass


def main(argv=None):
    ap = argparse.ArgumentParser()
    # Honour $PORT so hosting platforms (Render, Fly, …) can assign one.
    default_port = int(os.environ.get("CLARA_PORT") or os.environ.get("PORT") or 8000)
    ap.add_argument("--port", type=int, default=default_port)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args(argv)
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Clara reference UI on http://{args.host}:{args.port}  (Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
