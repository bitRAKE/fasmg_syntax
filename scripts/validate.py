#!/usr/bin/env python3
"""
Validate the fasmg test suite against a real fasmg binary.

Usage:
    python validate.py [--fasmg PATH_TO_FASMG]

Behaviour:
    * Every file under ../test_suit/pass/ must assemble with exit code 0.
    * Every file under ../test_suit/fail/ must fail with a non-zero exit code.

If --fasmg is not provided, the script searches PATH and a few well-known
locations on this machine.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITE = HERE.parent / "test_suit"
PASS_DIR = SUITE / "pass"
FAIL_DIR = SUITE / "fail"

DEFAULT_CANDIDATES = [
    r"C:\git\~tgrysztar\fasmg\core\fasmg.exe",
    r"C:\git\~tgrysztar\fasmg\fasmg.exe",
    "fasmg.exe",
    "fasmg",
]


def probe_version(fasmg: Path) -> str:
    """fasmg prints e.g. `flat assembler  version g.l4gs` on the first line
    when called with no arguments. The version token is freeform (not semver),
    so we just extract whatever follows `version `."""
    try:
        r = subprocess.run(
            [str(fasmg)], capture_output=True, text=True, timeout=5
        )
    except Exception:
        return "unknown"
    first = (r.stdout + r.stderr).splitlines()[:1]
    if not first:
        return "unknown"
    line = first[0].strip()
    marker = "version "
    i = line.find(marker)
    return line[i + len(marker):].strip() if i >= 0 else line


def find_fasmg(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit)
        if p.is_file():
            return p
        sys.exit(f"error: --fasmg path does not exist: {explicit}")
    for c in DEFAULT_CANDIDATES:
        found = shutil.which(c) if os.sep not in c else (c if Path(c).is_file() else None)
        if found:
            return Path(found)
    sys.exit(
        "error: could not locate fasmg. Pass --fasmg PATH_TO_FASMG or add it to PATH."
    )


def assemble(fasmg: Path, source: Path) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / (source.stem + ".bin")
        try:
            r = subprocess.run(
                [str(fasmg), str(source), str(out)],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            return 124, "timeout"
        return r.returncode, (r.stdout + r.stderr).strip()


def run() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fasmg", help="path to fasmg executable")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    fasmg = find_fasmg(args.fasmg)
    version = probe_version(fasmg)
    print(f"using fasmg: {fasmg}  (version {version})")

    failed: list[str] = []

    for src in sorted(PASS_DIR.glob("*.g")):
        rc, log = assemble(fasmg, src)
        ok = rc == 0
        print(f"  pass  {src.name:<40} {'OK' if ok else 'FAIL'}")
        if args.verbose or not ok:
            if log:
                print("    " + log.replace("\n", "\n    "))
        if not ok:
            failed.append(f"{src} expected success, got rc={rc}")

    for src in sorted(FAIL_DIR.glob("*.g")):
        rc, log = assemble(fasmg, src)
        ok = rc != 0
        print(f"  fail  {src.name:<40} {'OK' if ok else 'FAIL'}")
        if args.verbose or not ok:
            if log:
                print("    " + log.replace("\n", "\n    "))
        if not ok:
            failed.append(f"{src} expected failure, got rc=0")

    if failed:
        print("\n{} failure(s):".format(len(failed)))
        for f in failed:
            print(" -", f)
        return 1

    print("\nall good.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
