"""
Single source of truth for fasmg syntax.

All the regex fragments and keyword groups here have been verified against
fasmg `g.l4gs` (see ../test_suit/). When you change anything here, regenerate
all output formats with `python scripts/gen_all.py` and re-run `validate.py`.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Tokenisation
# ---------------------------------------------------------------------------

# Special characters that always terminate a name token. This list is exact
# (verified against the binary). The "trailing backslash joins next line"
# behaviour is pre-tokenisation, so `\` is always a terminator inside a name.
SPECIAL_CHARS = r"+-/*=<>()[]{}:?!,.|&~#`\\"

# Negated character class for "any single name character" (in regex source).
# Excludes the special set, plus whitespace and `;` (comment opener).
NAME_CHAR_CLASS = r"[^\s+\-/*=<>()\[\]{}:?!,.|&~`;\\]"

# ---------------------------------------------------------------------------
# Number literal patterns
# ---------------------------------------------------------------------------
#
# `_` and `'` are separators allowed after the first significant char of any
# base. The 0x prefix is lowercase ONLY. Float exponent and `f` suffix are
# mutually exclusive. See ../fasmg.syntax_notes.md for the full table.

NEG_NUM = r"(?<![\w.#])"  # ensure number doesn't continue an identifier

NUMBER_PATTERNS: list[tuple[str, str, str]] = [
    # (scope-suffix, comment, regex)
    (
        "hex",
        "Hex 0x... — lowercase x ONLY. Separators allowed anywhere after 0x.",
        NEG_NUM + r"0x[0-9A-Fa-f_']+",
    ),
    (
        "hex",
        "Hex $... — first char after $ MUST be a hex digit.",
        NEG_NUM + r"\$[0-9A-Fa-f][0-9A-Fa-f_']*",
    ),
    (
        "hex",
        "Hex with h/H suffix. Must start with 0-9.",
        NEG_NUM + r"[0-9][0-9A-Fa-f_']*[hH]\b",
    ),
    (
        "binary",
        "Binary with b/B suffix.",
        NEG_NUM + r"[01][01_']*[bB]\b",
    ),
    (
        "octal",
        "Octal with o/O/q/Q suffix.",
        NEG_NUM + r"[0-7][0-7_']*[oOqQ]\b",
    ),
    (
        "float",
        "Float with dot. Exponent and f suffix are mutually exclusive.",
        NEG_NUM + r"[0-9][0-9_']*\.[0-9][0-9_']*(?:(?:[eE][+-]?[0-9_']*[0-9][0-9_']*)|[fF])?\b",
    ),
    (
        "float",
        "Float without dot, with exponent (no f suffix allowed).",
        NEG_NUM + r"[0-9][0-9_']*[eE][+-]?[0-9_']*[0-9][0-9_']*\b",
    ),
    (
        "float",
        "Float without dot or exponent, with mandatory f suffix.",
        NEG_NUM + r"[0-9][0-9_']*[fF]\b",
    ),
    (
        "decimal",
        "Decimal with optional d/D suffix.",
        NEG_NUM + r"[0-9][0-9_']*[dD]?\b",
    ),
]

# ---------------------------------------------------------------------------
# String literal rules
# ---------------------------------------------------------------------------
# Strings are line-based; doubled quote is the only escape; an unclosed
# string is an error.

STRING_RULES = [
    {
        "quote": "'",
        "scope": "string.quoted.single.fasmg",
        "escape": "''",
    },
    {
        "quote": '"',
        "scope": "string.quoted.double.fasmg",
        "escape": '""',
    },
]

# ---------------------------------------------------------------------------
# Keyword groups (verified against the manual + the binary)
# ---------------------------------------------------------------------------

CONTROL_DIRECTIVES = [
    "if", "else if", "else match", "else",
    "end if", "end match", "end while", "end repeat",
    "end iterate", "end irp", "end irpv",
    "end macro", "end struc", "end namespace", "end virtual", "end postpone",
    "end",
    "while", "repeat", "rept", "iterate", "irp", "irpv",
    "match", "rawmatch", "rmatch",
    "postpone", "break", "continue",
    "namespace", "virtual", "assert", "outscope",
]

DATA_DIRECTIVES = [
    "db", "dw", "dd", "dp", "dq", "dt", "ddq", "dqq", "ddqq",
    "rb", "rw", "rd", "rp", "rq", "rt", "rdq", "rqq", "rdqq",
    "emit", "dbx", "file", "dup",
]

STORAGE_DIRECTIVES = [
    "equ", "reequ", "define", "redefine",
    "label", "element", "restore", "purge",
    "restruc", "mvmacro", "mvstruc", "esc", "local",
]

OTHER_DIRECTIVES = [
    "org", "section", "restartout", "load", "store",
    "format", "binary", "executable",
    "display", "err", "eval",
    "retaincomments", "removecomments",
    "isolatelines", "combinelines",
    "include",
]

WORD_OPERATORS = [
    "mod", "xor", "and", "or", "not",
    "shl", "shr", "bsf", "bsr", "bswap",
    "string", "lengthof", "bappend",
    "element", "scale", "metadata",
    "elementof", "scaleof", "metadataof", "elementsof",
    "sizeof", "float", "trunc",
    "eq", "eqtype", "relativeto",
    "defined", "definite", "used",
    "at", "from", "as",
]

SIZE_CONSTANTS = [
    "byte", "word", "dword", "fword", "pword", "qword",
    "tbyte", "tword", "dqword", "xword",
    "qqword", "yword", "dqqword", "zword",
]

CALM_COMMANDS = [
    "assemble", "match", "rawmatch",
    "arrange", "compute", "check",
    "publish", "transform", "stringify",
    "take", "taketext", "call", "local",
    "jyes", "jno", "jump", "exit",
    "emit", "display", "err", "load", "store",
]

CALM_MATCH_MODIFIERS = [
    "name", "expression", "number", "quoted",
    "equ", "macro", "struc",
    "priorequ", "priormacro", "priorstruc",
    "area",
]

BUILTIN_SYMBOLS = [
    r"\$\$", r"\$@", r"\$%%", r"\$%", r"\$",   # order matters: longest first
    "%%", "%t", "%",
    "__time__", "__file__", "__line__", "__source__",
]


def word_alt(words: list[str]) -> str:
    """Build a regex alternation that matches any of the words, treating
    embedded spaces in `words` (e.g. "end if") as `\\s+`."""
    parts = []
    for w in words:
        if " " in w:
            parts.append(r"\s+".join(map(_escape_word, w.split())))
        else:
            parts.append(_escape_word(w))
    # Sort longest-first so `else if` wins over `else`
    parts.sort(key=len, reverse=True)
    return "|".join(parts)


def _escape_word(w: str) -> str:
    # Word characters don't need escaping; punctuation does.
    return "".join((c if c.isalnum() or c == "_" else "\\" + c) for c in w)
