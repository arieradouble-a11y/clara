#!/usr/bin/env python3
"""Syntax-check the inline <script> in the zero-dependency reference UI.

The reference UI (web/index.html) has no build step, so nothing would otherwise
catch a JS syntax error in its inline script. This extracts that script and runs
`node --check` on it. Exits non-zero on a syntax error or if node is missing.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

HTML = Path(__file__).resolve().parent.parent / "web" / "index.html"


def main() -> int:
    text = HTML.read_text(encoding="utf-8")
    scripts = re.findall(r"<script>(.*?)</script>", text, re.DOTALL)
    if not scripts:
        print("No inline <script> found in web/index.html", file=sys.stderr)
        return 1
    ok = True
    for i, body in enumerate(scripts):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(body)
            path = f.name
        try:
            r = subprocess.run(["node", "--check", path], capture_output=True, text=True)
        except FileNotFoundError:
            print("node is required for the JS syntax check", file=sys.stderr)
            return 2
        finally:
            Path(path).unlink(missing_ok=True)
        if r.returncode != 0:
            ok = False
            print(f"Syntax error in inline script #{i + 1}:\n{r.stderr}", file=sys.stderr)
    if ok:
        print("web/index.html inline script: syntax OK")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
