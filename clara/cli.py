"""Command-line interface.

    clara simplify --text "..."            # rewrite + faithfulness report
    clara easyread --file doc.txt          # one idea per line + pictograms
    echo "..." | clara simplify --json     # machine-readable output
    clara score --file doc.txt             # just the readability numbers

Runs offline by default (mock provider). Point at a real model with, e.g.:
    CLARA_PROVIDER=anthropic ANTHROPIC_API_KEY=sk-... clara simplify --text "..."
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from .auth import AuthStore
from .easyread import easy_read
from .export import document_html
from .ingest import from_text, from_url, ingest_file
from .llm import get_check_provider, get_provider
from .pipeline import simplify_structured, simplify_text
from .readability import analyze
from .review import ReviewStore
from .semantic import semantic_check
from .serialize import easyread_dict, easyread_line_dict, readability_dict, result_dict
from .structure import block_dict


def _read_ingest(args):
    """Ingest the chosen input once, returning the full IngestResult (text +
    structural blocks), so callers can preserve headings/lists when they want to."""
    ocr = getattr(args, "ocr", "auto")
    if getattr(args, "url", None):
        return from_url(args.url)
    if args.text is not None:
        return from_text(args.text)
    if args.file:
        res = ingest_file(args.file, ocr=ocr)  # dispatches: txt / pdf / docx / html
        if res.ocr_applied:
            print("(OCR applied — text recovered from a scanned PDF)", file=sys.stderr)
        return res
    return from_text(sys.stdin.read())


def _read_input(args) -> str:
    return _read_ingest(args).text


def _fmt(v) -> str:
    return "n/a" if v is None else str(v)


def cmd_simplify(args) -> int:
    provider = get_provider(args.provider)
    ing = _read_ingest(args)

    # A structured source (DOCX/HTML with headings/lists) keeps its scaffolding
    # in the HTML export, unless the reader asks to flatten it.
    if args.html and ing.blocks and not args.flatten:
        sres = simplify_structured(ing.blocks, level=args.level, provider=provider,
                                   grade=args.grade, lang=args.lang)
        print(document_html(kind="structured", blocks=[block_dict(b) for b in sres.blocks],
                            lang=args.lang, title=ing.title or "Plain-language document",
                            footer="Simplified with Clara — assistive, not authoritative."))
        return 0

    res = simplify_text(ing.text, level=args.level, provider=provider,
                        grade=args.grade, lang=args.lang)
    fr = res.faithfulness

    if args.html:
        print(document_html(kind="text", text=res.simplified, lang=args.lang,
                            footer="Simplified with Clara — assistive, not authoritative."))
        return 0

    if args.json:
        print(json.dumps(result_dict(res), ensure_ascii=False, indent=2))
        return 0

    src, out = res.source_readability, res.output_readability
    print(f"--- Simplified ({res.level}) ---")
    print(res.simplified)
    print()
    print(f"Readability : grade {_fmt(src.flesch_kincaid_grade)} -> {_fmt(out.flesch_kincaid_grade)}"
          f"   (Flesch ease {src.flesch_reading_ease} -> {out.flesch_reading_ease})")

    if fr.ok and not fr.warnings:
        print("Faithfulness: OK - all numbers and dates preserved.")
    else:
        print("Faithfulness: REVIEW")
        if fr.dropped_quantities:
            print("  Dropped numbers:", ", ".join(fr.dropped_quantities))
        if fr.invented_quantities:
            print("  Invented numbers:", ", ".join(fr.invented_quantities))
        if fr.dropped_dates:
            print("  Dropped dates:", ", ".join(fr.dropped_dates))
        if fr.invented_dates:
            print("  Invented dates:", ", ".join(fr.invented_dates))
        if fr.dropped_identifiers:
            print("  Dropped identifiers:", ", ".join(fr.dropped_identifiers))
        if fr.invented_identifiers:
            print("  Invented identifiers:", ", ".join(fr.invented_identifiers))
        for w in fr.warnings:
            print("  ! ", w)

    if args.semantic:
        checker = get_check_provider(args.check_provider)
        rep = semantic_check(res.original, res.simplified, provider=checker, lang=args.lang)
        grader = args.check_provider or os.environ.get("CLARA_CHECK_PROVIDER")
        if not rep.available:
            print("AI check    : unavailable (configure a real provider)")
        elif rep.faithful and not rep.issues:
            note = f" (graded by {grader})" if grader else ""
            print(f"AI check    : faithful (no meaning drift){note}")
        else:
            print("AI check    : REVIEW")
            for i in rep.issues:
                print(f"  - {i.type}: {i.detail}")
    return 0


def cmd_easyread(args) -> int:
    provider = get_provider(args.provider)
    res = easy_read(_read_input(args), provider=provider, lang=args.lang,
                    with_pictograms=not args.no_pictograms, symbols=args.symbols)

    if args.html:
        lines = [easyread_line_dict(ln) for ln in res.lines]
        print(document_html(kind="easyread", lines=lines, lang=args.lang, title="Easy Read document",
                            footer="Simplified with Clara — assistive, not authoritative.",
                            embed_images=args.embed_images))
        return 0

    if args.json:
        print(json.dumps(easyread_dict(res), ensure_ascii=False, indent=2))
        return 0

    print("--- Easy Read ---")
    for ln in res.lines:
        pic = f"[{ln.pictogram_id}: {ln.keyword}]" if ln.pictogram_id else "[no picture]"
        print(f"  {pic}  {ln.text}")
        if ln.image_url:
            print(f"      {ln.image_url}")
    out = res.output_readability
    print(f"\nReadability : grade {_fmt(out.flesch_kincaid_grade)}   (Flesch ease {out.flesch_reading_ease})")
    fr = res.faithfulness
    if fr.ok and not fr.warnings:
        print("Faithfulness: OK - all numbers and dates preserved.")
    else:
        print("Faithfulness: REVIEW", "".join(f"\n  ! {w}" for w in fr.warnings))
    return 0


def cmd_score(args) -> int:
    r = analyze(_read_input(args), lang=args.lang)
    print(json.dumps(readability_dict(r), indent=2))
    return 0


def cmd_review_list(args) -> int:
    rows = ReviewStore().list_reviews(status=args.status)
    if not rows:
        print("No reviews.")
        return 0
    for r in rows:
        print(f'#{r["id"]:<4} {r["status"]:<18} {r["lang"]}/{r["level"]:<8} {r["title"]}')
    return 0


def cmd_review_show(args) -> int:
    r = ReviewStore().get_review(args.id)
    if not r:
        print(f"Review #{args.id} not found.")
        return 1
    print(f'#{r["id"]} [{r["status"]}] {r["title"]}  ({r["lang"]}/{r["level"]}/{r["kind"]})')
    print("\n-- Source --\n" + r["source"])
    print("\n-- Output --\n" + r["output"])
    if r["comments"]:
        print("\n-- Comments --")
        for c in r["comments"]:
            print(f'  [{c["created_at"]}] {c["author"]}: {c["body"]}')
    print(f'\nVersions: {len(r["versions"])}')
    return 0


def cmd_review_status(args) -> int:
    try:
        r = ReviewStore().set_status(args.id, args.status)
    except ValueError as e:
        print(e)
        return 1
    if not r:
        print(f"Review #{args.id} not found.")
        return 1
    print(f'#{r["id"]} -> {r["status"]}')
    return 0


def cmd_profile_example(args) -> int:
    from .profile import EXAMPLE_PROFILE

    print(json.dumps(EXAMPLE_PROFILE, ensure_ascii=False, indent=2))
    return 0


def cmd_profile_check(args) -> int:
    from .profile import validate_profile

    try:
        with open(args.file, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    errors = validate_profile(data)
    if errors:
        for problem in errors:
            print(f"error: {problem}", file=sys.stderr)
        return 1
    print("Profile is valid.")
    return 0


def cmd_profile_render(args) -> int:
    from .profile import load_profile, render_instructions

    try:
        prof = load_profile(args.file)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    text = render_instructions(prof)
    if not text:
        print("(empty profile — nothing to render)", file=sys.stderr)
        return 1
    print(text)
    return 0


def cmd_user_add(args) -> int:
    import getpass

    password = args.password or getpass.getpass("Password: ")
    try:
        u = AuthStore().create_user(args.username, password, role=args.role)
    except ValueError as e:
        print(e)
        return 1
    print(f"created user '{u['username']}' (role {u['role']})")
    return 0


def cmd_user_list(args) -> int:
    users = AuthStore().list_users()
    if not users:
        print("No users.")
        return 0
    for u in users:
        print(f'{u["id"]:<4} {u["role"]:<10} {u["username"]}')
    return 0


def _add_io_args(p) -> None:
    src = p.add_mutually_exclusive_group()
    src.add_argument("--text", help="Text to process (default: read stdin)")
    src.add_argument("--file", help="Read text/PDF/DOCX/HTML from this file")
    src.add_argument("--url", help="Fetch and extract the main text from this URL")
    p.add_argument("--ocr", default="auto", choices=["auto", "force", "off"],
                   help="OCR a scanned PDF: auto (default, if it looks scanned), force, or off")


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # Windows consoles default to cp1251
    except Exception:
        pass

    parser = argparse.ArgumentParser(prog="clara", description="Turn complex text into verified plain language.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("simplify", help="Rewrite text and check faithfulness")
    _add_io_args(s)
    s.add_argument("--level", default="plain", choices=["plain", "easy_read", "grade"])
    s.add_argument("--grade", type=int, default=None, help="Target grade for --level grade")
    s.add_argument("--lang", default="en", help="Language pack (en, ru)")
    s.add_argument("--provider", default=None, help="mock | openai | anthropic | ollama")
    s.add_argument("--semantic", action="store_true", help="Also run an LLM semantic faithfulness check")
    s.add_argument("--check-provider", default=None,
                   help="Provider for the --semantic check, so a model doesn't grade its own "
                        "rewrite (default: CLARA_CHECK_PROVIDER, else the simplify provider)")
    s.add_argument("--html", action="store_true", help="Output an accessible HTML document")
    s.add_argument("--flatten", action="store_true",
                   help="With --html, drop source headings/lists and emit plain paragraphs")
    s.add_argument("--json", action="store_true", help="Machine-readable output")
    s.set_defaults(func=cmd_simplify)

    e = sub.add_parser("easyread", help="Easy Read: one idea per line, paired with pictograms")
    _add_io_args(e)
    e.add_argument("--lang", default="en", help="Language pack (en, ru) — also the ARASAAC locale")
    e.add_argument("--provider", default=None, help="mock | openai | anthropic | ollama")
    e.add_argument("--no-pictograms", action="store_true", help="Skip pictogram lookup (offline)")
    e.add_argument("--symbols", default=None, choices=["arasaac", "mulberry"],
                   help="Symbol set: arasaac (CC BY-NC-SA, default) or mulberry (CC BY-SA, commercial-ok)")
    e.add_argument("--html", action="store_true", help="Output an accessible HTML document")
    e.add_argument("--embed-images", action="store_true",
                   help="Inline pictograms as data URIs so the HTML works offline (with --html)")
    e.add_argument("--json", action="store_true", help="Machine-readable output")
    e.set_defaults(func=cmd_easyread)

    sc = sub.add_parser("score", help="Show readability metrics only")
    _add_io_args(sc)
    sc.add_argument("--lang", default="en", help="Language pack (en, ru)")
    sc.set_defaults(func=cmd_score)

    rv = sub.add_parser("review", help="Inspect the review workflow store")
    rvsub = rv.add_subparsers(dest="review_cmd", required=True)
    rl = rvsub.add_parser("list", help="List reviews")
    rl.add_argument("--status", default=None, help="Filter by status")
    rl.set_defaults(func=cmd_review_list)
    rs = rvsub.add_parser("show", help="Show one review")
    rs.add_argument("id", type=int)
    rs.set_defaults(func=cmd_review_show)
    rt = rvsub.add_parser("status", help="Set a review's status")
    rt.add_argument("id", type=int)
    rt.add_argument("status", help="draft|in_review|approved|rejected|changes_requested")
    rt.set_defaults(func=cmd_review_status)

    pf = sub.add_parser("profile", help="Accessibility profile tools (docs/accessibility-profile.md)")
    pfsub = pf.add_subparsers(dest="profile_cmd", required=True)
    pe = pfsub.add_parser("example", help="Print a starter profile (redirect to a file and edit)")
    pe.set_defaults(func=cmd_profile_example)
    pc = pfsub.add_parser("check", help="Validate a profile file")
    pc.add_argument("--file", required=True, help="Path to the profile JSON")
    pc.set_defaults(func=cmd_profile_check)
    pr = pfsub.add_parser("render",
                          help="Render a profile as model instructions — paste into any chat client")
    pr.add_argument("--file", required=True, help="Path to the profile JSON")
    pr.set_defaults(func=cmd_profile_render)

    u = sub.add_parser("user", help="Manage review users (for CLARA_AUTH)")
    usub = u.add_subparsers(dest="user_cmd", required=True)
    ua = usub.add_parser("add", help="Create a user (the first user becomes admin)")
    ua.add_argument("username")
    ua.add_argument("--password", default=None, help="Password (prompted if omitted)")
    ua.add_argument("--role", default=None, choices=["admin", "reviewer"])
    ua.set_defaults(func=cmd_user_add)
    ul = usub.add_parser("list", help="List users")
    ul.set_defaults(func=cmd_user_list)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except RuntimeError as e:
        # Missing optional dependency (pypdf / python-docx / [ocr]) or a bad
        # document — report it cleanly instead of dumping a traceback.
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
