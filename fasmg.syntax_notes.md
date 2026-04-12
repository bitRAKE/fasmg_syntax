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

---

# Part 2 — Deeper Layers: Disambiguation and Semantics

The rules above (Part 1) are sufficient for **surface-level** syntax highlighting —
tokenising, colouring keywords, matching block pairs. But tools that go deeper
(Tree-sitter grammars, LSP servers, linters) must also understand the structural
and semantic layers below. This section documents those layers, verified against
fasmg `g.l4gs`.

## Symbol classes and line-position disambiguation

Every name in fasmg can simultaneously hold meanings in up to **three** independent
symbol classes:

| Class | How defined | How invoked (line position) |
|---|---|---|
| **Expression** | `= := =: equ reequ define redefine` | Anywhere except the positions below |
| **Instruction** | `macro … end macro`, `calminstruction … end calminstruction` | First non-label identifier on a line |
| **Labeled-instruction** | `struc … end struc`, `calminstruction (target) …` | Second position: `label Name …` |

The same name `bar` can be all three simultaneously:

```fasmg
define bar 42           ; expression class
macro bar               ; instruction class
  db 0AAh
end macro
struc bar               ; labeled-instruction class
  label .:byte
  .x db ?
end struc

dd bar                  ; expression: 42
bar                     ; instruction: macro (emits 0xAA)
myobj bar               ; labeled-instruction: struc
```

### Label chaining on a single line

Multiple labels can precede an instruction on the same line:

```fasmg
a: b: c: db 0FFh        ; three labels, all pointing to the same address
```

A label followed by a labeled-instruction also works:

```fasmg
first: second emit_one   ; first = label, second = labeled-instruction target
```

### Per-class removal

| Directive | Removes from class | Syntax |
|---|---|---|
| `restore name` | Expression | Prefix directive |
| `purge name` | Instruction | Prefix directive |
| `restruc name` | Labeled-instruction | Prefix directive |

Each removes only the **top** meaning in that class, revealing the one beneath.

## Symbol stacking (define/restore/purge)

Definitions in fasmg are **stacked**, not overwritten. Each `define`/`equ`/`macro`/
`struc` pushes a new meaning onto the name's stack for its class. `restore`/`purge`/
`restruc` peel the top meaning, revealing the prior one.

```fasmg
define myval 1
define myval 2
define myval 3
dd myval              ; 3  (top of stack)
restore myval         ; peel
dd myval              ; 2
restore myval         ; peel
dd myval              ; 1
```

### reequ / redefine — replace-top (no stack push)

`reequ` (infix) and `redefine` (prefix) replace the current top-of-stack without
pushing a new entry:

```fasmg
myval equ 1
myval equ 2
myval reequ 99        ; replaces 2 with 99 (stack depth unchanged)
dd myval              ; 99
restore myval
dd myval              ; 1  (only one restore needed)
```

### Shadowing keywords and built-ins

**Any** name can be shadowed — including keywords (`db`, `if`, `while`) and built-in
symbols (`$`, `%`, `byte`). After shadowing, the name resolves to the user definition.
After `restore`/`purge`, the built-in meaning returns as a fallback:

```fasmg
define db 42          ; shadow the 'db' data directive
dd db                 ; expression: 42 (not a directive)
restore db
db 0                  ; directive again

define $ 99           ; shadow current-address built-in
dd $                  ; 99
restore $             ; $ is current-address again
```

### mvmacro / mvstruc — rename across classes

`mvmacro newname, oldname` moves the instruction-class meaning. `mvstruc` does the
same for labeled-instruction class. The old name loses its meaning in that class.

## Assignment syntax: prefix vs infix

Fasmg has two syntactic families for symbol definition:

| Form | Syntax | Example |
|---|---|---|
| **Infix** | `name OP value` | `x = 1`, `x := 2`, `x =: $`, `x equ 3`, `x reequ 4` |
| **Prefix** | `KEYWORD name value` | `define x 5`, `redefine x 6`, `label x:byte at $`, `element x` |

This distinction matters for parsers: infix forms look like `identifier operator expression`,
while prefix forms look like `keyword identifier expression`. A Tree-sitter grammar must
handle both without confusing one for the other.

## Angle-bracket groups

Angle brackets `< >` serve as **argument group delimiters** in several contexts:

- **Macro arguments**: `gatherer <1,2,3>, <4,5,6>` — commas inside `< >` don't split arguments.
- **`define` values**: `define PARAMS <1,2,3>` — the value includes commas.
- **`match` source**: `match =A,=B, PARAMS` — where `PARAMS` expands to `<1,2,3>`.
- **`iterate` variable groups**: `iterate <a,b>, 1,10, 2,20` — paired iteration variables.
- **CALM `match` bracket pair**: `match from-to, def, ()` — third argument selects brackets.

Angle brackets are **not operators** — they are structural grouping tokens that only
have meaning at the argument-parsing level. A grammar should treat them as opaque
delimiters, not as comparison operators in this context.

## CALM `match` — sigils, bracket pairs, and wildcard modifiers

CALM `match` has up to 4 arguments: `match pattern, source [, bracket-or-sigil [, …]]`.

### Bracket pair (3rd argument is two chars)

When the 3rd argument is a bracket pair like `()`, `[]`, `<>`, `{}`, it enables
**balanced matching** — wildcards in the pattern can match text containing those brackets
as long as they are balanced:

```fasmg
calminstruction range definition
    match   from-to, definition, ()
    emit    1, from
    emit    1, to
end calminstruction
range (10-3)-10       ; from = (10-3), to = 10  (balanced parens)
```

### Sigil character (3rd argument is one char)

When the 3rd argument is a single special character (`:`, `/`, `-`, `.`, etc.), it
becomes the **wildcard modifier sigil**. A wildcard followed by `sigil + modifier`
restricts what it matches:

| Modifier | Matches |
|---|---|
| `name` | A complete symbol identifier |
| `expression` | A well-structured expression (may be unevaluated) |
| `number` | A numeric literal (integer or float) |
| `quoted` | A quoted string |
| `equ` | An identifier with a defined expression-class meaning |
| `macro` | An identifier with a defined instruction-class meaning |
| `struc` | An identifier with a defined labeled-instruction-class meaning |
| `priorequ` | Like `equ` but must be defined earlier (no forward refs) |
| `priormacro` | Like `macro` but earlier |
| `priorstruc` | Like `struc` but earlier |
| `area` | An area label identifier |

Example with `:` as sigil:

```fasmg
match   var:name val, var, :    ; :name restricts 'var' to match a symbol name only
```

Example with `/` as sigil:

```fasmg
match   text/expression, text, /   ; /expression restricts 'text' to a valid expression
```

**Constraint**: Bracket balancing and wildcard modifying cannot be combined in the same
`match` command. Also, specialized wildcards cannot be made optional.

## The `outscope` directive

`outscope` evaluates its argument line in the **parent scope** (one macro expansion
level up). This is how macros can define globally-visible symbols:

```fasmg
macro defglobal name*, val*
  outscope name equ val
end macro
defglobal myglob, 42
dd myglob             ; 42
```

## Implications for parser/grammar design

### What a syntax grammar CAN resolve
- Tokenisation: numbers, strings, identifiers, operators, comments
- Block structure: keyword-pair delimited blocks (`if`…`end if`, etc.)
- CALM as a structurally distinct region
- Label definitions (`:` and `::`)
- Assignment form (infix vs prefix)
- Angle-bracket group boundaries

### What a syntax grammar CANNOT resolve (semantic layer required)
- Which symbol class a name resolves in at a given position (requires tracking
  all `define`/`macro`/`struc` and `restore`/`purge`/`restruc` across passes)
- Whether a name is shadowed or built-in at a given point
- Whether an identifier is an instruction, expression, or labeled-instruction target
  (depends on all prior definitions, potentially across `include` files)
- Forward reference resolution (fasmg is multi-pass)
- `retaincomments` / `isolatelines` mode changes (alter tokenisation at runtime)

> **The Tree-sitter grammar models fasmg syntax and structure, not final symbol
> meaning.** Because names in fasmg may be shadowed, stacked, restored, purged,
> or rebound across symbol classes, downstream tooling should treat semantic
> resolution as a separate analysis layer built on top of the parse tree.

---

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
