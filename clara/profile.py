"""LLM accessibility profile — a small portable spec, and its reference tools.

Operating systems have accessibility settings that applications respect. Games
ship remappable controls and readable-font modes. The LLM ecosystem has nothing:
every chat starts from zero, and the person least able to re-explain their needs
("write short sentences, no hard words") is the one who must do it most often.

A profile is a tiny JSON document that states those needs once — reading level,
sentence length, formatting, verification — so any chat client can apply it.
The format is defined in docs/accessibility-profile.md (+ JSON Schema alongside).
This module is the reference implementation:

    validate_profile(dict)   -> list of problems ([] = valid)
    render_instructions(p)   -> deterministic system-prompt text (Mode A:
                                paste into ANY chat client; a request, not a
                                guarantee)
    proxy_options(p)         -> clara-proxy options (Mode B: the verified path,
                                where reading level is enforced by the pipeline
                                and fact loss is checked, not hoped for)
    reading_notes(p)         -> extra constraints for simplify()'s system prompt
    load_profile(path)       -> parsed + validated, or ValueError

This module is dependency-free on purpose — the spec should be implementable
in a hundred lines in any language, and this file is the proof.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

SPEC_VERSION = "0.1"

_LEVELS = {"plain", "easy_read", "grade"}
_LANG_NAMES = {"en": "English", "ru": "Russian", "es": "Spanish", "de": "German", "fr": "French"}

EXAMPLE_PROFILE: dict = {
    "a11y_profile": SPEC_VERSION,
    "language": "en",
    "reading": {
        "level": "easy_read",
        "max_sentence_words": 15,
        "one_idea_per_line": True,
        "define_hard_words": True,
    },
    "format": {
        "prefer_lists": True,
        "avoid_tables": True,
        "avoid_emoji": True,
        "short_answers": True,
    },
    "verify": {"facts": True, "warn_inline": True},
    "symbols": {"set": "arasaac"},
}


def validate_profile(profile) -> list[str]:
    """Problems with a profile, [] when valid. Unknown fields are never errors —
    the spec requires implementations to ignore what they don't understand, so a
    newer profile still works (degraded, not broken) with an older client."""
    if not isinstance(profile, dict):
        return ["profile must be a JSON object"]
    errors: list[str] = []
    if not isinstance(profile.get("a11y_profile"), str) or not profile.get("a11y_profile"):
        errors.append("'a11y_profile' (spec version string) is required")
    if "language" in profile and not isinstance(profile["language"], str):
        errors.append("'language' must be a string language code (e.g. 'ru')")

    reading = profile.get("reading", {})
    if not isinstance(reading, dict):
        errors.append("'reading' must be an object")
        reading = {}
    level = reading.get("level")
    if level is not None and level not in _LEVELS:
        errors.append(f"reading.level must be one of: {', '.join(sorted(_LEVELS))}")
    grade = reading.get("grade")
    if grade is not None and (isinstance(grade, bool) or not isinstance(grade, int) or not 1 <= grade <= 12):
        errors.append("reading.grade must be an integer from 1 to 12")
    msw = reading.get("max_sentence_words")
    if msw is not None and (isinstance(msw, bool) or not isinstance(msw, int) or msw < 3):
        errors.append("reading.max_sentence_words must be an integer >= 3")

    bool_fields = (
        ("reading", reading, ("one_idea_per_line", "define_hard_words")),
        ("format", profile.get("format", {}), ("prefer_lists", "avoid_tables", "avoid_emoji", "short_answers")),
        ("verify", profile.get("verify", {}), ("facts", "warn_inline")),
    )
    for name, section, keys in bool_fields:
        if not isinstance(section, dict):
            if name != "reading":  # reading already reported above
                errors.append(f"'{name}' must be an object")
            continue
        for key in keys:
            if key in section and not isinstance(section[key], bool):
                errors.append(f"{name}.{key} must be true or false")

    symbols = profile.get("symbols", {})
    if not isinstance(symbols, dict):
        errors.append("'symbols' must be an object")
    elif "set" in symbols and not isinstance(symbols["set"], str):
        errors.append("symbols.set must be a string")
    return errors


def render_instructions(profile: dict, *, include_reading: bool = True) -> str:
    """The profile as a deterministic instruction block for a system prompt.

    This is Mode A — portable to any model or client, but a *request*: nothing
    checks the model obeyed. include_reading=False is for pipelines (like
    clara-proxy) where the reading level is enforced by a verified simplify pass
    instead, so only the language and formatting wishes go to the model.
    """
    lines: list[str] = []
    lang = profile.get("language")
    if lang:
        lines.append(f"Always answer in {_LANG_NAMES.get(str(lang).lower(), str(lang))}.")

    reading = profile.get("reading") or {}
    if include_reading and isinstance(reading, dict):
        level = reading.get("level")
        if level == "easy_read":
            lines.append("Use Easy Read style: very short sentences, the simplest everyday words, "
                         "and speak directly to the reader.")
        elif level == "grade":
            lines.append(f"Write at a US grade {reading.get('grade', 5)} reading level.")
        elif level == "plain":
            lines.append("Use plain language: short sentences, everyday words, active voice.")
        if reading.get("max_sentence_words"):
            lines.append(f"Keep every sentence under {int(reading['max_sentence_words'])} words.")
        if reading.get("one_idea_per_line"):
            lines.append("Write one idea per sentence, one sentence per line.")
        if reading.get("define_hard_words"):
            lines.append("Explain any hard word in simple terms the first time you use it.")

    fmt = profile.get("format") or {}
    if isinstance(fmt, dict):
        if fmt.get("prefer_lists"):
            lines.append("Prefer short bulleted lists over long paragraphs.")
        if fmt.get("avoid_tables"):
            lines.append("Do not use tables; give the same information as plain sentences or lists.")
        if fmt.get("avoid_emoji"):
            lines.append("Do not use emoji or decorative symbols.")
        if fmt.get("short_answers"):
            lines.append("Keep answers as short as the question allows. Do not pad.")

    if not lines:
        return ""
    head = "ACCESSIBILITY PROFILE — the reader needs these rules followed in every answer:"
    return head + "\n" + "\n".join(f"- {line}" for line in lines)


def reading_notes(profile: dict) -> str:
    """Reading-detail constraints as extra style lines for simplify()'s system
    prompt — the fields the fixed level styles don't pin down exactly."""
    reading = profile.get("reading") or {}
    if not isinstance(reading, dict):
        return ""
    lines: list[str] = []
    if reading.get("max_sentence_words"):
        lines.append(f"- Keep every sentence under {int(reading['max_sentence_words'])} words.")
    if reading.get("one_idea_per_line"):
        lines.append("- Write one idea per sentence, one sentence per line.")
    if reading.get("define_hard_words"):
        lines.append("- Explain any hard word in simple terms.")
    return "\n".join(lines)


def proxy_options(profile: dict) -> dict:
    """The profile mapped onto clara-proxy options (Mode B, the verified path)."""
    out: dict = {}
    reading = profile.get("reading") or {}
    if isinstance(reading, dict):
        if reading.get("level"):
            out["level"] = reading["level"]
        if reading.get("grade") is not None:
            out["grade"] = reading["grade"]
    if profile.get("language"):
        out["lang"] = profile["language"]
    ver = profile.get("verify") or {}
    if isinstance(ver, dict):
        if ver.get("warn_inline") is not None:
            out["annotate"] = bool(ver["warn_inline"])
        if ver.get("facts") is False:  # no fact wish -> never annotate either
            out["annotate"] = False
    return out


def load_profile(path) -> dict:
    """Read and validate a profile file; ValueError with every problem listed."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = validate_profile(data)
    if errors:
        raise ValueError("Invalid accessibility profile: " + "; ".join(errors))
    return data


def load_env_profile() -> dict | None:
    """The profile named by CLARA_PROFILE, or None when unset.

    A broken file raises instead of being skipped: a silently dropped
    accessibility profile is the worst failure mode — the person believes their
    protections are on."""
    path = os.environ.get("CLARA_PROFILE")
    if not path:
        return None
    try:
        return load_profile(path)
    except Exception as e:
        raise RuntimeError(f"CLARA_PROFILE could not be loaded from {path}: {e}") from e
