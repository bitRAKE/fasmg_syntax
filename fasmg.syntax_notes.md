# fasmg Syntax Notes

Source: `https://github.com/tgrysztar/fasmg/tree/master/core/docs\{fasmg,manual}.txt`. These are the
rules that drove `fasmg.tmLanguage.json`.

## Lines & comments
- One command per line. `;` starts a comment to end-of-line.
- Trailing `\` joins the next line to the current one (unless `isolatelines`).
- `retaincomments` disables `;` as a comment marker (treats it as a token),
  `removecomments` restores it. `combinelines` / `isolatelines` toggle `\` joining.

## Tokens
- Special single-char tokens: `+-/*=<>()[]{}:?!,.|&~#\`` and `\`.
- Any other contiguous run of non-whitespace is a name or number.

## Strings (line-based, single escape)
- Start with `'` or `"`, must be closed by the **same quote on the same line**.
- An unclosed string (EOL/EOF before closing quote) is an **error**.
- The only escape is doubling the quote: `''` inside `'...'`, `""` inside `"..."`.
- Quotes themselves are not part of the string.
- In the grammar, the `end` pattern captures either the closing quote
  (`punctuation.definition.string.end`) or end-of-line
  (`invalid.illegal.unclosed-string`) so editors can highlight the error.

## Numbers (advanced — with `_` and `'` separators)

A token is numeric iff it **starts with a decimal digit**, or starts with `$`
followed immediately by a hex digit. If neither holds, the token is treated as
an identifier (or, for `$` alone, the current-address symbol).

Separators `_` and `'` may appear **after the first mandatory character**, in
any quantity, including adjacently. They cannot be the leading character of
the token.

### Per-base rules (verified against fasmg `g.l4gs`)

| Form | Pattern | Notes |
|---|---|---|
| Decimal | `[0-9][0-9_']*[dD]?` | `1_000`, `1'000'000`, `10D` all valid |
| Binary  | `[01][01_']*[bB]` | `1010'1010b`, case-insensitive suffix |
| Octal   | `[0-7][0-7_']*[oOqQ]` | `0777o`, `7_7q` |
| Hex `0x…` | `0x[0-9A-Fa-f_']+` | **Lowercase `x` only**. `0X1` is rejected. Separators allowed anywhere after `0x`, including immediately: `0x_0`, `0x_` (= 0), `0xDE'AD'BE'EF` all valid. |
| Hex `$…` | `$[0-9A-Fa-f][0-9A-Fa-f_']*` | First char after `$` must be a hex digit. `$_0` is parsed as the identifier `$_0`, not a number. `$` alone is the current-address symbol. |
| Hex `…h` | `[0-9][0-9A-Fa-f_']*[hH]` | Must start with `0-9`. `_0h` is an identifier. `0_h`, `0'0h`, `10H` all valid. Cannot combine with `0x`: `0xab_h` is rejected. |
| Float (dot) | `[0-9][0-9_']*\.[0-9][0-9_']*((eE…)|f)?` | Both sides of `.` require at least one digit. `1.e5` is rejected. |
| Float (exp, no dot) | `[0-9][0-9_']*[eE][+-]?[0-9_']*[0-9][0-9_']*` | `1e5` is a float. |
| Float (f only) | `[0-9][0-9_']*[fF]` | `0f`, `1_f` are floats. |

### Float exclusivity rule

**The exponent `e…` and the `f` suffix are mutually exclusive.**

| Literal | Result |
|---|---|
| `1.5`      | ✓ |
| `1.5e5`    | ✓ |
| `1.5e5f`   | ✗ invalid number |
| `1e5`      | ✓ |
| `1e5f`     | ✗ invalid number |
| `1f`       | ✓ |
| `1.0f`     | ✓ |

### Separator corner cases

Separators flow freely once the first significant char has been emitted —
including in exponents, even adjacent to `e`:

| Literal | Result |
|---|---|
| `1_000_000`       | ✓ |
| `1'000'000`       | ✓ |
| `1__0`, `1''0`, `1_'0`, `1'_0` | ✓ (multiple/mixed consecutive) |
| `1_`, `1'`        | ✓ (trailing) |
| `_1`              | ✗ (leading — parses as identifier) |
| `0x_`             | ✓ (= 0) |
| `0x__0`, `0x0__0` | ✓ |
| `$_0`             | ✗ (identifier, not a number) |
| `_0h`             | ✗ (identifier, not a number) |
| `0h_`             | ✗ invalid number (no characters allowed after the base suffix) |
| `0_d_d`           | ✗ only one base-suffix character allowed |
| `1.0e_10`         | ✓ |
| `1.0e+_10`        | ✓ |
| `1.0e10_`         | ✓ |
| `1.5e05`          | ✓ |
| `.5`              | ✗ (must start with a digit) |

### Suffix casing

- `b/B`, `d/D`, `o/O`, `q/Q`, `h/H`, `f/F` are **all case-insensitive**.
- `0x` prefix is **case-sensitive**: only lowercase `x` is accepted.

## Identifiers

### Tokenisation

A name is a maximal run of **non-special, non-whitespace** characters that
does **not** start with a decimal digit (else it's a number) and does **not**
start with `$` immediately followed by a hex digit (else it's a number).

The special characters that always terminate a name token are the exact set
listed in the manual:

```
+ - / * = < > ( ) [ ] { } : ? ! , . | & ~ # ` \
```

Plus whitespace and `;` (comment). `\` is always a terminator — the
"trailing backslash joins the next line" behaviour is handled at a stage
before tokenisation, so you can never have `\` inside a name.

Everything else is a name character, including some surprises verified
against fasmg `g.l4gs`:

| Char | In name? | Note |
|---|---|---|
| letters `A-Za-z` | ✓ | default, case-sensitive |
| digits `0-9` | ✓ | not as the first char |
| `_` | ✓ | |
| `@` `^` `%` `$` | ✓ | all are plain name characters mid-token |
| `"` `'` | ✓ **mid-token only** | `foo"bar`, `a'b'c` are valid identifiers. Quotes only start a string when they are the first character of a contiguous non-whitespace sequence. |
| `\` | ✗ | special character; always terminates a name |
| ` ` `\t` | ✗ | whitespace terminates a token |
| `;` | ✗ | starts a comment to end-of-line |
| Unicode | ✓ | letters, CJK, emoji — `café`, `日本`, `🙂` all work |

### Leading-character rules

| Start | Interpreted as |
|---|---|
| digit `0-9` | number |
| `$` + hex digit | number (`$A`, `$DEAD`) |
| `$` + non-hex, non-terminator | identifier (`$G`, `$_`) |
| `$` alone (terminator follows) | the current-address built-in |
| `.`, `..`, `…` | identifier in parent/unnamed namespace |
| `?` | identifier with instruction-suppression (`?namespace = 0`) |
| `#` | identifier (concatenation marker, see below) |
| anything else non-special | identifier |

Identifiers **cannot** start with `_`, `@`, `^`, `%`, a digit, or `$` + hex
digit? — wait, `_foo`, `@foo`, `^foo`, `%foo`, `%%foo` all work (they just
happen not to look like number starts). Only leading *digits* and
`$`+*hex-digit* get diverted into the number branch.

### Namespacing and modifiers

- **Case sensitivity**: identifiers are case-sensitive by default. Appending
  `?` (no whitespace) to a name segment marks it case-insensitive: `name?`.
  `?` **may not appear in the middle of a name**: `fo?o` is rejected. As a
  whole-identifier prefix, `?foo` and `?ns.foo` are valid (it suppresses
  instruction-class interpretation), but `ns.?foo` is rejected — `?` can only
  precede the **first** name segment.
- **Dot chaining**: `space.color.r`. **No whitespace is allowed around dots.**
  `foo. bar` and `foo .bar` are both rejected.
- **Leading dots**: a single leading `.` refers to the most-recent parent
  label's namespace; two or more leading dots refer to distinct unnamed
  special namespaces (one per dot count).
- **Dots-in-the-middle, numeric segments**: after a dot, a "name segment" is
  allowed to start with a digit and may even contain token content that
  doesn't form a valid number. `ns.1`, `ns.01`, `ns.0x`, `ns.0x1`, `ns.1b`,
  `ns.1e5`, `ns.1.2.3` are all valid identifiers. The number-vs-name rule
  only applies at the **very start** of the whole identifier.
- **`#`** is the concatenation / context-break marker. It can appear
  anywhere inside an identifier (including leading or trailing) without
  changing the meaning; when placed between two name tokens it forces them
  to concatenate (and apply the recognition context to the first one).
- **Labels**: `name:` (ordinary label — allows another command on the same
  line), `name::` (area label, for use with `load`/`store`).

### Reserved / built-in identifiers

Not actually reserved — **can be shadowed by user definitions**:

- `$`, `$$`, `$@`, `$%`, `$%%` — current address / area base / uninit base /
  output offset / file offset
- `%`, `%%` — repeat/iterate counters (only meaningful inside a repeating
  block; outside, they are ordinary names and can be assigned)
- `%t`, `__time__`, `__file__`, `__line__`, `__source__` — built-in
  constants; all can be redefined as user symbols
- built-in size constants `byte?`, `word?`, … `zword?`

The built-in meaning persists even after `restore`/`purge` — it comes back
as the fallback when the user definition is removed.

## Symbol classes
Expression / instruction / labeled-instruction; same name can occupy multiple
classes simultaneously. First identifier on a line is resolved as instruction;
second as labeled instruction; anywhere else as expression.

## Operators
- Arithmetic: `+ - * /`, `mod`.
- Bitwise: `and or xor not shl shr bsf bsr bswap`.
- Strings: `string`, `lengthof`, `bappend`.
- Polynomial/element: `element scale metadata elementof scaleof metadataof
  elementsof sizeof`.
- Float: `float trunc` (`bsr`, `shl`, `shr` also accept floats).
- Logical (in `if`/`while`/`assert`/`check`): `~ & |` plus relations
  `= < > <= >= <>`, `eq eqtype relativeto defined definite used`.
- `` ` `` stringifies a parameter name.

## Core directives
- Data: `db dw dd dp dq dt ddq dqq ddqq` / `rb rw rd rp rq rt rdq rqq rdqq` /
  `emit` (alias `dbx`) / `file` / `dup`.
- Symbols: `= := =: equ reequ define redefine label element restore purge
  restruc mvmacro mvstruc`.
- Control: `if / else if / else / end if`, `while / end while`,
  `repeat|rept / end repeat`, `iterate|irp / end iterate`,
  `irpv / end irpv`, `match / else match / end match`, `rawmatch|rmatch`,
  `break`, `postpone / end postpone`, `namespace / end namespace`,
  `virtual / end virtual`, `assert`, `outscope`.
- Macros: `macro / end macro`, `struc / end struc`, `local`, `esc`.
  Trailing `!` on name = unconditional. `:` after name = recursive/constant.
  `(label) name` on `struc` captures the label text.
  Parameter modifiers: `?` (case-ins), `*` (required), `:default`, `&`
  (consume rest of line, no added context), `` ` `` (stringify).
- Output: `org section restartout load store format (binary|executable) as`.
- Source/output control: `include[!]`, `eval`, `display`, `err`,
  `retaincomments removecomments isolatelines combinelines`.
- Built-ins: `byte word dword fword pword qword tbyte tword dqword xword
  qqword yword dqqword zword`; `$ $$ $@ $% $%%`, `% %%`, `__time__ __file__
  __line__ __source__`, legacy `%t`.

## CALM — the language-inside-a-language
`calminstruction [(label)] name[!][?] [args] … end calminstruction` defines an
instruction written in a different, compiled sub-language. Inside the block:
- Lines are CALM commands, not normal assembly. Labels (`name:`) are only
  meaningful as jump targets for `jump`/`jyes`/`jno`.
- Arguments are symbolic variables, not preprocessed parameters; all symbol
  references are resolved/fixed at **definition** time.
- Commands:
  - Flow: `assemble`, `jump`, `jyes`, `jno`, `exit`, `call`.
  - Parameters/text: `match`, `arrange`, `transform`, `stringify`, `take`,
    `taketext`, `local`, `publish`.
  - Numeric/logic: `compute`, `check`.
  - Output: `emit`, `display`, `err`, `load`, `store` (these take
    pre-compiled expressions and raw offsets — different syntax from their
    base-language namesakes).
- CALM `match` extras:
  - Optional 3rd argument: bracket pair for balanced matching, **or** a single
    special char that becomes the wildcard-modifier sigil.
  - Wildcard modifiers: `name`, `expression`, `number`, `quoted`,
    `equ`, `macro`, `struc`, `priorequ`, `priormacro`, `priorstruc`, `area`.
  - `name?` variant on a wildcard makes it optional (empty-matchable).
- Custom CALM commands may be defined as macros or calminstructions in the
  `calminstruction?.…?` namespace (e.g. `calminstruction?.init?`).

## Grammar implications
- **Line-based strings**: string rules use `'…'(?!')|$` and `"…"(?!")|$` and
  accept only doubled-quote escapes.
- **Numbers**: patterns permit `[_']` between digits of every base.
- **Comments**: plain `;` to EOL — simple `begin/end` with `end: $`.
- **CALM DSL**: a dedicated `begin`/`end` region
  (`calminstruction` … `end calminstruction`) with its own repository of
  commands and match modifiers, falling back to shared strings/numbers/etc.
- **Line continuation**: trailing `\` highlighted separately (not consumed by
  any other rule).
- **Identifiers**: `?` suffix recognized as case-insensitive marker;
  leading dots and embedded `#`/`.` preserved as single token.
