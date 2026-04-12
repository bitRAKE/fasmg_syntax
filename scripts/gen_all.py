#!/usr/bin/env python3
"""Generate all fasmg syntax files from the single source of truth (spec.py).

Usage:
    python scripts/gen_all.py          # generate everything into dist/
    python scripts/gen_all.py --lint   # also run the regex linter
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DIST = ROOT / "dist"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lint", action="store_true", help="run regex lint after generation")
    args = ap.parse_args()

    DIST.mkdir(parents=True, exist_ok=True)

    # -- TextMate ---------------------------------------------------------
    from gen_textmate import write as write_tm
    write_tm(DIST / "fasmg.tmLanguage.json")

    # -- Notepad++ UDL ----------------------------------------------------
    from gen_npp import write as write_npp
    write_npp(DIST / "fasmg.udl.xml")

    print(f"\nall outputs written.")

    # -- Lint (optional) --------------------------------------------------
    if args.lint:
        from lint_grammar import lint
        ok = lint(DIST / "fasmg.tmLanguage.json")
        if not ok:
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
