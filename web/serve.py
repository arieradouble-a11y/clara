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
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make 'clara' importable

from clara.easyread import easy_read  # noqa: E402
from clara.llm import get_provider  # noqa: E402
from clara.pipeline import simplify_text  # noqa: E402
from clara.readability import analyze  # noqa: E402
from clara.serialize import easyread_dict, faithfulness_dict, readability_dict, result_dict  # noqa: E402
from clara.verify import verify  # noqa: E402

INDEX = Path(__file__).resolve().parent / "index.html"


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n).decode("utf-8")) if n else {}

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
                res = easy_read(data.get("text", ""), provider=provider, lang=data.get("lang", "en"))
                self._send_json(easyread_dict(res))
            else:
                self._send_json({"error": "not found"}, 404)
        except Exception as e:  # keep the dev server up; surface the message to the UI
            self._send_json({"error": f"{type(e).__name__}: {e}"}, 400)

    def log_message(self, *args):  # quieter console
        pass


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("CLARA_PORT", 8000)))
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
