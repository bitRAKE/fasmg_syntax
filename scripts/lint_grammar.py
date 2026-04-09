#!/usr/bin/env python3
"""Lint a TextMate grammar JSON file by compiling every regex with Python `re`.

This catches typos, unbalanced groups, and invalid escape sequences before
the grammar is loaded in an editor. It does NOT guarantee TextMate/Oniguruma
compatibility — Python's regex engine is a subset — but it's a good first pass.

Usage:
    python scripts/lint_grammar.py [path/to/fasmg.tmLanguage.json]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_GRAMMAR = HERE.parent / "fasmg.tmLanguage.json"

# Keys in the grammar JSON that contain regex strings.
REGEX_KEYS = {"match", "begin", "end"}


def _collect_patterns(obj, path="$") -> list[tuple[str, str]]:
    """Walk the grammar tree and collect (json-path, regex-string) pairs."""
    found = []
    if isinstance(obj, dict):
        for key, val in obj.items():
            if key in REGEX_KEYS and isinstance(val, str):
                found.append((f"{path}.{key}", val))
            else:
                found.extend(_collect_patterns(val, f"{path}.{key}"))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            found.extend(_collect_patterns(item, f"{path}[{i}]"))
    return found


def lint(grammar_path: Path) -> bool:
    """Return True if all patterns compile, False otherwise."""
    with grammar_path.open(encoding="utf-8") as f:
        grammar = json.load(f)

    patterns = _collect_patterns(grammar)
    errors = []
    for path, regex in patterns:
        try:
            re.compile(regex)
        except re.error as e:
            errors.append((path, regex, str(e)))

    if errors:
        print(f"lint: {len(errors)} invalid regex(es) in {grammar_path.name}:")
        for path, regex, msg in errors:
            print(f"  {path}")
            print(f"    pattern: {regex}")
            print(f"    error:   {msg}")
        return False

    print(f"lint: all {len(patterns)} regex patterns OK in {grammar_path.name}")
    return True


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_GRAMMAR
    if not path.exists():
        sys.exit(f"error: {path} not found. Run gen_all.py first.")
    ok = lint(path)
    raise SystemExit(0 if ok else 1)
