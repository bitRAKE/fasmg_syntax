"""Generate fasmg.tmLanguage.json from spec.py."""
from __future__ import annotations

import json
from pathlib import Path

import spec


def kw_match(words, scope, *, case_insensitive=True):
    """Build a TextMate `match` rule for a word list with no-identifier
    boundaries on either side."""
    flag = "(?i)" if case_insensitive else ""
    return {
        "name": scope,
        "match": f"{flag}(?<![\\w.#])(?:{spec.word_alt(words)})(?![\\w.#?])",
    }


def number_patterns():
    out = []
    for suffix, comment, pat in spec.NUMBER_PATTERNS:
        out.append(
            {
                "comment": comment,
                "name": f"constant.numeric.{suffix}.fasmg",
                "match": pat,
            }
        )
    return out


def string_patterns():
    out = []
    for r in spec.STRING_RULES:
        q = r["quote"]
        # In JSON we need a literal quote in the regex; the doubled-quote
        # escape is `r["escape"]` already.
        out.append(
            {
                "comment": (
                    f"Line-based; doubled {q*2} is the only escape; "
                    "unclosed at EOL is an error."
                ),
                "name": r["scope"],
                "begin": q,
                "end": f"(?:({q}(?!{q})))|(\\n|$)",
                "beginCaptures": {
                    "0": {"name": "punctuation.definition.string.begin.fasmg"}
                },
                "endCaptures": {
                    "1": {"name": "punctuation.definition.string.end.fasmg"},
                    "2": {"name": "invalid.illegal.unclosed-string.fasmg"},
                },
                "patterns": [
                    {
                        "name": "constant.character.escape.fasmg",
                        "match": r["escape"] if q == "'" else r["escape"],
                    }
                ],
            }
        )
    return out


def build_grammar() -> dict:
    name_char = spec.NAME_CHAR_CLASS
    return {
        "$schema": "https://raw.githubusercontent.com/martinring/tmlanguage/master/tmlanguage.json",
        "name": "flat assembler g",
        "scopeName": "source.fasmg",
        "fileTypes": ["asm", "inc", "fasmg", "g"],
        "patterns": [{"include": "#line"}],
        "repository": {
            "line": {
                "patterns": [
                    {"include": "#comment"},
                    {"include": "#line-continuation"},
                    {"include": "#calminstruction-block"},
                    {"include": "#strings"},
                    {"include": "#label-definition"},
                    {"include": "#preprocessor"},
                    {"include": "#macro-definition-head"},
                    {"include": "#control-directives"},
                    {"include": "#data-directives"},
                    {"include": "#storage-directives"},
                    {"include": "#directives"},
                    {"include": "#operators-word"},
                    {"include": "#size-constants"},
                    {"include": "#special-symbols"},
                    {"include": "#numbers"},
                    {"include": "#operators-punct"},
                    {"include": "#identifiers"},
                ]
            },
            "comment": {
                "name": "comment.line.semicolon.fasmg",
                "begin": ";",
                "end": "$",
                "beginCaptures": {
                    "0": {"name": "punctuation.definition.comment.fasmg"}
                },
            },
            "line-continuation": {
                "name": "constant.character.escape.continuation.fasmg",
                "match": "\\\\\\s*$",
            },
            "strings": {"patterns": string_patterns()},
            "numbers": {
                "comment": "See fasmg.syntax_notes.md for the verified rules.",
                "patterns": number_patterns(),
            },
            "label-definition": {
                "match": "^\\s*([A-Za-z_.?#][\\w.?#]*)\\s*(::?)(?!=)",
                "captures": {
                    "1": {"name": "entity.name.label.fasmg"},
                    "2": {"name": "punctuation.separator.label.fasmg"},
                },
            },
            "preprocessor": {
                "patterns": [
                    {
                        "name": "meta.preprocessor.include.fasmg",
                        "begin": "(?i)\\b(include)\\b(!)?",
                        "end": "$",
                        "beginCaptures": {
                            "1": {"name": "keyword.control.import.fasmg"},
                            "2": {
                                "name": "keyword.operator.unconditional.fasmg"
                            },
                        },
                        "patterns": [
                            {"include": "#comment"},
                            {"include": "#strings"},
                            {"include": "#numbers"},
                            {"include": "#identifiers"},
                        ],
                    }
                ]
            },
            "macro-definition-head": {
                "match": "(?i)^\\s*(macro|struc)\\b(!)?\\s*(?:\\(\\s*([A-Za-z_?][\\w.?#]*)\\s*\\)\\s*)?([A-Za-z_.?#][\\w.?#]*)?",
                "captures": {
                    "1": {"name": "storage.type.macro.fasmg"},
                    "2": {"name": "keyword.operator.unconditional.fasmg"},
                    "3": {"name": "variable.parameter.label.fasmg"},
                    "4": {"name": "entity.name.function.macro.fasmg"},
                },
            },
            "control-directives": kw_match(
                spec.CONTROL_DIRECTIVES, "keyword.control.fasmg"
            ),
            "data-directives": kw_match(
                spec.DATA_DIRECTIVES, "keyword.other.data.fasmg"
            ),
            "storage-directives": kw_match(
                spec.STORAGE_DIRECTIVES, "storage.type.fasmg"
            ),
            "directives": kw_match(
                spec.OTHER_DIRECTIVES, "keyword.other.directive.fasmg"
            ),
            "operators-word": kw_match(
                spec.WORD_OPERATORS, "keyword.operator.word.fasmg"
            ),
            "size-constants": {
                "name": "support.constant.size.fasmg",
                "match": "(?i)(?<![\\w.#])(?:"
                + spec.word_alt(spec.SIZE_CONSTANTS)
                + ")\\??(?![\\w.#])",
            },
            "special-symbols": {
                "patterns": [
                    {
                        "name": "variable.language.address.fasmg",
                        "match": "\\$(?:\\$|@|%%|%)?",
                    },
                    {
                        "name": "variable.language.repeat-counter.fasmg",
                        "match": "(?<![\\w.#])%%?(?![\\w.#])",
                    },
                    {
                        "name": "support.constant.builtin.fasmg",
                        "match": "(?<![\\w.#])__(?:time|file|line|source)__(?![\\w.#])",
                    },
                    {
                        "name": "support.constant.builtin.fasmg",
                        "match": "(?<![\\w.#])%t(?![\\w.#])",
                    },
                ]
            },
            "operators-punct": {
                "patterns": [
                    {
                        "name": "keyword.operator.assignment.fasmg",
                        "match": ":=|=:|==|=",
                    },
                    {
                        "name": "keyword.operator.comparison.fasmg",
                        "match": "<=|>=|<>|<|>",
                    },
                    {
                        "name": "keyword.operator.logical.fasmg",
                        "match": "[&|~]",
                    },
                    {
                        "name": "keyword.operator.arithmetic.fasmg",
                        "match": "[+\\-*/]",
                    },
                    {
                        "name": "keyword.operator.context.fasmg",
                        "match": "[`#]",
                    },
                    {
                        "name": "punctuation.separator.fasmg",
                        "match": "[,:]",
                    },
                    {
                        "name": "punctuation.section.parens.fasmg",
                        "match": "[()\\[\\]{}]",
                    },
                    {
                        "name": "keyword.operator.modifier.fasmg",
                        "match": "[!?]",
                    },
                ]
            },
            "identifiers": {
                "comment": (
                    "Maximal run of non-special non-whitespace chars; quotes "
                    "are name chars mid-token (only string-starters at a "
                    "token boundary). Verified against fasmg g.l4gs."
                ),
                "patterns": [
                    {
                        "match": (
                            r"\??(?:[.]+)?"
                            + name_char
                            + name_char
                            + r"*\??(?:[.#]+"
                            + name_char
                            + r"+\??)*"
                        ),
                        "name": "variable.other.fasmg",
                    }
                ],
            },
            "calminstruction-block": {
                "comment": "DSL within the language: calminstruction ... end calminstruction.",
                "begin": "(?i)^\\s*(calminstruction)\\b(!)?\\s*(?:\\(\\s*([A-Za-z_?][\\w.?#]*)\\s*\\)\\s*)?([A-Za-z_.?#][\\w.?#]*)?",
                "end": "(?i)^\\s*(end\\s+calminstruction)\\b",
                "beginCaptures": {
                    "1": {"name": "storage.type.calminstruction.fasmg"},
                    "2": {"name": "keyword.operator.unconditional.fasmg"},
                    "3": {"name": "variable.parameter.label.fasmg"},
                    "4": {
                        "name": "entity.name.function.calminstruction.fasmg"
                    },
                },
                "endCaptures": {
                    "1": {"name": "storage.type.calminstruction.fasmg"}
                },
                "name": "meta.calminstruction.fasmg",
                "patterns": [
                    {"include": "#comment"},
                    {"include": "#line-continuation"},
                    {"include": "#strings"},
                    {"include": "#calm-label"},
                    {"include": "#calm-commands"},
                    {"include": "#calm-match-modifiers"},
                    {"include": "#operators-word"},
                    {"include": "#size-constants"},
                    {"include": "#special-symbols"},
                    {"include": "#numbers"},
                    {"include": "#operators-punct"},
                    {"include": "#identifiers"},
                ],
            },
            "calm-label": {
                "match": "^\\s*([A-Za-z_][\\w]*)\\s*(:)(?!=)",
                "captures": {
                    "1": {"name": "entity.name.label.calm.fasmg"},
                    "2": {"name": "punctuation.separator.label.fasmg"},
                },
            },
            "calm-commands": kw_match(
                spec.CALM_COMMANDS, "keyword.control.calm.fasmg"
            ),
            "calm-match-modifiers": kw_match(
                spec.CALM_MATCH_MODIFIERS, "support.type.calm-modifier.fasmg"
            ),
        },
    }


def write(out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(build_grammar(), f, indent=2)
        f.write("\n")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    write(Path(__file__).parent.parent / "fasmg.tmLanguage.json")
