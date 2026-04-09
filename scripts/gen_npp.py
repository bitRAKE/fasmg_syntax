"""Generate a Notepad++ User-Defined Language file (UDL v2.1) for fasmg.

The UDL format is XML. Notepad++ matches keyword groups whole-token only,
so case-insensitive directives just need to be listed in lowercase with
the case-insensitive flag set on the language root.
"""
from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET
from xml.dom import minidom

import spec


def kw(words: list[str]) -> str:
    """UDL keyword lists are space-separated tokens. Multi-word entries
    like 'end if' are not natively supported by UDL keyword groups, so we
    drop them — Notepad++ will still highlight `end` and `if` separately."""
    flat = []
    for w in words:
        for part in w.split():
            if part not in flat:
                flat.append(part)
    return " ".join(flat)


def build() -> ET.Element:
    nlang = ET.Element(
        "NotepadPlus"
    )
    udl = ET.SubElement(
        nlang,
        "UserLang",
        attrib={
            "name": "fasmg",
            "ext": "asm inc fasmg g",
            "udlVersion": "2.1",
        },
    )

    settings = ET.SubElement(udl, "Settings")
    ET.SubElement(
        settings, "Global", attrib={
            "caseIgnored": "yes",
            "allowFoldOfComments": "no",
            "foldCompact": "no",
            "forcePureLC": "0",
            "decimalSeparator": "0",
        },
    )
    ET.SubElement(
        settings, "Prefix", attrib={
            "Keywords1": "no", "Keywords2": "no", "Keywords3": "no",
            "Keywords4": "no", "Keywords5": "no", "Keywords6": "no",
            "Keywords7": "no", "Keywords8": "no",
        },
    )

    klists = ET.SubElement(udl, "KeywordLists")

    def kwlist(name: str, value: str) -> None:
        e = ET.SubElement(klists, "Keywords", attrib={"name": name})
        e.text = value

    # Comment / number prefixes (UDL slot definitions)
    kwlist("Comments", "00; 01 02((EOL))")
    kwlist(
        "Numbers, prefix1", "0x"
    )
    kwlist("Numbers, prefix2", "$")
    kwlist("Numbers, extras1", "_ '")
    kwlist("Numbers, extras2", "")
    kwlist("Numbers, suffix1", "h H")
    kwlist("Numbers, suffix2", "b B o O q Q d D f F")
    kwlist("Numbers, range", "0 1 2 3 4 5 6 7 8 9 A B C D E F a b c d e f")

    kwlist("Operators1", "+ - / * = < > ( ) [ ] { } : ? ! , . | & ~ # ` \\")
    kwlist("Operators2", "")

    # Folding pairs (one set per nesting level fasmg supports)
    kwlist("Folders in code1, open", "macro struc calminstruction namespace virtual postpone if while repeat rept iterate irp irpv match rawmatch rmatch")
    kwlist("Folders in code1, middle", "else")
    kwlist("Folders in code1, close", "end")
    kwlist("Folders in code2, open", "")
    kwlist("Folders in code2, middle", "")
    kwlist("Folders in code2, close", "")
    kwlist("Folders in comment, open", "")
    kwlist("Folders in comment, middle", "")
    kwlist("Folders in comment, close", "")

    # Eight keyword slots — UDL convention. We map fasmg's groups onto them.
    kwlist("Keywords1", kw(spec.CONTROL_DIRECTIVES))
    kwlist("Keywords2", kw(spec.DATA_DIRECTIVES))
    kwlist("Keywords3", kw(spec.STORAGE_DIRECTIVES))
    kwlist("Keywords4", kw(spec.OTHER_DIRECTIVES))
    kwlist("Keywords5", kw(spec.WORD_OPERATORS))
    kwlist("Keywords6", kw(spec.SIZE_CONSTANTS))
    kwlist("Keywords7", kw(spec.CALM_COMMANDS))
    kwlist("Keywords8", kw(spec.CALM_MATCH_MODIFIERS))

    kwlist("Delimiters", '00\' 01 02\' 03" 04 05"')

    # Style definitions — colours kept neutral; users can theme in NPP.
    styles = ET.SubElement(udl, "Styles")

    def style(name: str, fg="000000", bg="FFFFFF", style="0"):
        ET.SubElement(
            styles, "WordsStyle",
            attrib={
                "name": name, "fgColor": fg, "bgColor": bg,
                "fontName": "", "fontStyle": style, "nesting": "0",
            },
        )

    style("DEFAULT")
    style("COMMENTS",       fg="008000", style="2")
    style("LINE COMMENTS",  fg="008000", style="2")
    style("NUMBERS",        fg="FF8000")
    style("KEYWORDS1",      fg="0000FF", style="1")  # control
    style("KEYWORDS2",      fg="800080")             # data directives
    style("KEYWORDS3",      fg="0080C0")             # storage
    style("KEYWORDS4",      fg="0080C0")             # other directives
    style("KEYWORDS5",      fg="000080", style="1")  # word operators
    style("KEYWORDS6",      fg="808000")             # size constants
    style("KEYWORDS7",      fg="0000FF", style="1")  # CALM commands
    style("KEYWORDS8",      fg="800040")             # CALM modifiers
    style("OPERATORS",      fg="000000", style="1")
    style("FOLDER IN CODE1",fg="000000", style="1")
    style("FOLDER IN CODE2", fg="000000")
    style("FOLDER IN COMMENT", fg="008000")
    style("DELIMITERS1",    fg="800000")
    style("DELIMITERS2",    fg="800000")
    style("DELIMITERS3",    fg="000000")
    style("DELIMITERS4",    fg="000000")
    style("DELIMITERS5",    fg="000000")
    style("DELIMITERS6",    fg="000000")
    style("DELIMITERS7",    fg="000000")
    style("DELIMITERS8",    fg="000000")

    return nlang


def write(out_path: Path) -> None:
    tree = build()
    rough = ET.tostring(tree, encoding="utf-8", xml_declaration=True)
    pretty = minidom.parseString(rough).toprettyxml(indent="    ", encoding="utf-8")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(pretty)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    write(Path(__file__).parent.parent / "dist" / "fasmg.udl.xml")
