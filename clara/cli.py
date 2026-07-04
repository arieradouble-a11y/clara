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
import sys

from .easyread import easy_read
from .llm import get_provider
from .pipeline import simplify_text
from .readability import analyze
from .serialize import easyread_dict, readability_dict, result_dict


def _read_input(args) -> str:
    if args.text is not None:
        return args.text
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            return f.read()
    return sys.stdin.read()


def cmd_simplify(args) -> int:
    provider = get_provider(args.provider)
    res = simplify_text(_read_input(args), level=args.level, provider=provider, grade=args.grade)
    fr = res.faithfulness

    if args.json:
        print(json.dumps(result_dict(res), ensure_ascii=False, indent=2))
        return 0

    src, out = res.source_readability, res.output_readability
    print(f"--- Simplified ({res.level}) ---")
    print(res.simplified)
    print()
    print(f"Readability : grade {src.flesch_kincaid_grade} -> {out.flesch_kincaid_grade}"
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
        for w in fr.warnings:
            print("  ! ", w)
    return 0


def cmd_easyread(args) -> int:
    provider = get_provider(args.provider)
    res = easy_read(_read_input(args), provider=provider, lang=args.lang,
                    with_pictograms=not args.no_pictograms)

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
    print(f"\nReadability : grade {out.flesch_kincaid_grade}   (Flesch ease {out.flesch_reading_ease})")
    fr = res.faithfulness
    if fr.ok and not fr.warnings:
        print("Faithfulness: OK - all numbers and dates preserved.")
    else:
        print("Faithfulness: REVIEW", "".join(f"\n  ! {w}" for w in fr.warnings))
    return 0


def cmd_score(args) -> int:
    r = analyze(_read_input(args))
    print(json.dumps(readability_dict(r), indent=2))
    return 0


def _add_io_args(p) -> None:
    src = p.add_mutually_exclusive_group()
    src.add_argument("--text", help="Text to process (default: read stdin)")
    src.add_argument("--file", help="Read text from this file")


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1251
    except Exception:
        pass

    parser = argparse.ArgumentParser(prog="clara", description="Turn complex text into verified plain language.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("simplify", help="Rewrite text and check faithfulness")
    _add_io_args(s)
    s.add_argument("--level", default="plain", choices=["plain", "easy_read", "grade"])
    s.add_argument("--grade", type=int, default=None, help="Target grade for --level grade")
    s.add_argument("--provider", default=None, help="mock | openai | anthropic | ollama")
    s.add_argument("--json", action="store_true", help="Machine-readable output")
    s.set_defaults(func=cmd_simplify)

    e = sub.add_parser("easyread", help="Easy Read: one idea per line, paired with pictograms")
    _add_io_args(e)
    e.add_argument("--lang", default="en", help="Pictogram language (ARASAAC locale)")
    e.add_argument("--provider", default=None, help="mock | openai | anthropic | ollama")
    e.add_argument("--no-pictograms", action="store_true", help="Skip pictogram lookup (offline)")
    e.add_argument("--json", action="store_true", help="Machine-readable output")
    e.set_defaults(func=cmd_easyread)

    sc = sub.add_parser("score", help="Show readability metrics only")
    _add_io_args(sc)
    sc.set_defaults(func=cmd_score)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
