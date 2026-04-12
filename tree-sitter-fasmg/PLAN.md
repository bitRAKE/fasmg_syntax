# Tree-sitter Grammar for fasmg — Implementation Plan

## Overview

This document plans a Tree-sitter grammar for **fasmg** (flat assembler g),
Tomasz Grysztar's bare assembly engine. fasmg is *not* a fixed-ISA assembler —
it is a programmable macro engine whose entire instruction set is defined by
packages loaded at runtime. The grammar therefore focuses on the **core
language** (directives, operators, CALM DSL, literals, identifiers) rather
than any specific target architecture.

Source of truth: `../scripts/spec.py` and `../fasmg.syntax_notes.md`.

---

## 1. Challenges Specific to fasmg

### 1.1 Line-oriented, not expression-oriented
fasmg processes one command per line (with `\` continuation). There is no
block-delimiting punctuation like `{}`; blocks are delimited by keyword
pairs (`macro`…`end macro`, `if`…`end if`, etc.). Tree-sitter's default
expectation of brace-delimited blocks doesn't apply.

### 1.2 The CALM DSL (language-within-a-language)
`calminstruction … end calminstruction` blocks contain a *different* command
set (assemble, arrange, compute, check, publish, match, jump, jyes, jno,
exit, etc.) with different label semantics (labels are jump targets only)
and different expression resolution (symbols fixed at definition time).
This requires either:
- A **separate grammar** composed via Tree-sitter's multi-language injection
  mechanism, or
- A **single grammar** with a dedicated `_calm_statement` branch activated
  inside `calminstruction_block` nodes.

**Recommendation**: single grammar with a `calm_block` node whose children
are `calm_statement` nodes. This avoids the complexity of multi-language
injection while still giving distinct node types for CALM commands. The
`calm_match` command's wildcard modifiers (name, expression, number, quoted,
equ, macro, struc, priorequ, priormacro, priorstruc, area) become their own
node type.

### 1.3 Identifier tokenisation is unusual
- Special characters `+-/*=<>()[]{}:?!,.|&~#`\` always terminate a name.
- Quotes (`'`, `"`) are name characters *mid-token* but string delimiters
  at the start of a token. Tree-sitter's lexer is character-level, so we
  handle this with a custom scanner (external scanner in C).
- `$` followed by a hex digit starts a number; followed by anything else
  it's part of an identifier (or the `$` built-in alone).
- `?` as a suffix marks case-insensitivity; as a prefix it suppresses
  instruction-class lookup. It cannot appear mid-name.
- `.` chains namespace segments with no whitespace allowed around it.
  After a dot, segments may start with digits.
- `#` is the concatenation marker, valid anywhere in an identifier.
- Unicode is fully supported in names (letters, CJK, emoji).

### 1.4 Number literals with separators
`_` and `'` are valid separators anywhere after the first significant
character. Multiple/mixed/trailing separators are allowed. Six base forms
(decimal, binary, octal, three hex variants) plus three float forms, with
mutual exclusivity between exponent `e` and suffix `f`. This is complex
enough to warrant an external scanner entry point rather than pure
Tree-sitter regex rules.

### 1.5 Context-dependent keyword interpretation
The same identifier can exist as an expression symbol, an instruction, and
a labeled instruction simultaneously. The first identifier on a line resolves
as instruction; the second as labeled instruction; elsewhere as expression.
Tree-sitter doesn't do multi-pass resolution, so we parse structurally
(first token = potential instruction) and leave semantic disambiguation to
downstream tooling.

### 1.6 User-redefinable built-ins
`$`, `$$`, `%`, `byte`, `word`, etc. can all be shadowed. The grammar
should tag them with node types but cannot enforce "this is always built-in."

---

## 2. Grammar Design

### 2.1 Top-level structure

```
source_file := (_statement '\n')*

_statement :=
  | comment
  | label_definition _statement?      ; label: or label:: followed by optional command
  | directive_statement
  | calm_block
  | macro_definition
  | struc_definition
  | assignment_statement               ; name = expr / name := expr / etc.
  | instruction_statement              ; catch-all: name [args]
  | _expression                        ; bare expression (rare but legal)
```

### 2.2 Block structures (keyword-pair delimited)

```
if_block        := 'if' condition '\n' body ('else' 'if' condition '\n' body)* ('else' '\n' body)? 'end' 'if'
while_block     := 'while' condition '\n' body 'end' 'while'
repeat_block    := ('repeat'|'rept') expr '\n' body 'end' 'repeat'
iterate_block   := ('iterate'|'irp') params '\n' body 'end' 'iterate'
irpv_block      := 'irpv' params '\n' body 'end' 'irpv'
match_block     := ('match'|'rawmatch'|'rmatch') pattern '\n' body ('else' 'match' pattern '\n' body)* 'end' 'match'
namespace_block := 'namespace' name '\n' body 'end' 'namespace'
virtual_block   := 'virtual' [expr] '\n' body 'end' 'virtual'
postpone_block  := 'postpone' '\n' body 'end' 'postpone'
macro_def       := 'macro' ['!'] [name] [params] '\n' body 'end' 'macro'
struc_def       := 'struc' ['!'] ['(' label ')'] [name] [params] '\n' body 'end' 'struc'
calm_block      := 'calminstruction' ['!'] ['(' label ')'] [name] [params] '\n' calm_body 'end' 'calminstruction'
```

Case-insensitive matching: Tree-sitter supports `word` tokens that can be
case-folded. We'll define all keywords in lowercase and use the
`word` field in `grammar.js` with a custom `word` regex.

### 2.3 CALM block internals

```
calm_body := (calm_statement '\n')*

calm_statement :=
  | comment
  | calm_label ':' calm_command?
  | calm_command

calm_command :=
  | calm_assemble
  | calm_arrange
  | calm_compute
  | calm_check
  | calm_match          ; with optional wildcard modifiers & bracket pair
  | calm_rawmatch
  | calm_publish
  | calm_transform
  | calm_stringify
  | calm_take
  | calm_taketext
  | calm_jump
  | calm_jyes
  | calm_jno
  | calm_exit
  | calm_call
  | calm_local
  | calm_emit
  | calm_display
  | calm_err
  | calm_load
  | calm_store
```

Each CALM command has slightly different argument syntax (e.g., `compute`
takes a destination and an expression; `match` takes a target, pattern, and
optional bracket/sigil argument). These will be individual grammar rules.

### 2.4 Expressions

```
_expression :=
  | number_literal
  | string_literal
  | identifier
  | special_symbol          ; $, $$, $@, $%, $%%, %, %%, %t, __time__, etc.
  | unary_expression        ; +, -, not, ~
  | binary_expression       ; +, -, *, /, mod, and, or, xor, shl, shr, etc.
  | paren_expression        ; ( expr )
  | sizeof_expression       ; sizeof name
  | elementof_expression    ; elementof / scaleof / metadataof / elementsof
  | float_expression        ; float expr
  | trunc_expression        ; trunc expr
  | string_op_expression    ; string expr / lengthof expr / bappend(expr, expr)
  | comparison              ; =, <, >, <=, >=, <>, eq, eqtype, relativeto
  | defined_check           ; defined name / definite name / used name
  | stringify_expression    ; ` name
  | size_override           ; byte expr / word expr / etc.
```

Operator precedence (Tree-sitter handles via `prec()`):
1. Unary: `+`, `-`, `not`, `~`, `float`, `trunc`, `string`, `lengthof`,
   `sizeof`, `elementof`, `scaleof`, `metadataof`, `elementsof`,
   `bsf`, `bsr`, `bswap`
2. Multiplicative: `*`, `/`, `mod`
3. Additive: `+`, `-`
4. Shift: `shl`, `shr`
5. Bitwise AND: `and`
6. Bitwise XOR: `xor`
7. Bitwise OR: `or`
8. Comparison: `=`, `<>`, `<`, `>`, `<=`, `>=`, `eq`, `eqtype`, `relativeto`
9. Logical NOT: `~`
10. Logical AND: `&`
11. Logical OR: `|`

### 2.5 Literals

**Numbers**: handled by an external scanner for precision. The scanner
reads the first character and dispatches:
- `0` + `x` → hex `0x…` branch
- `$` + hex-digit → `$…` hex branch
- `0-9` → decimal/binary/octal/hex-suffix/float branch (lookahead for
  suffix to determine base)

**Strings**: line-based, opened by `'` or `"` at a token boundary only.
Closed by the matching quote (not doubled). Doubled quote is the escape.
Unclosed at EOL is an error node. External scanner handles the "only at
token boundary" rule.

### 2.6 External scanner (C)

Required for:
1. **Identifiers** — mid-token quote handling, `$` disambiguation,
   `?`/`#`/`.` structural rules, Unicode.
2. **Number literals** — separator rules, base detection, float exclusivity.
3. **Strings** — token-boundary-only opening, line-based closing,
   unclosed-string error.
4. **Line continuation** — `\` at EOL joins next line.
5. **Comment** — `;` to EOL (needs to respect `retaincomments` state? —
   probably not; Tree-sitter is stateless, so we always treat `;` as
   comment start, which is the default and overwhelmingly common case).

The external scanner will be in `src/scanner.c`.

---

## 3. File Structure

```
tree-sitter-fasmg/
├── PLAN.md                  ← this file
├── grammar.js               ← Tree-sitter grammar definition
├── src/
│   ├── scanner.c            ← external scanner (identifiers, numbers, strings)
│   └── ...                  ← auto-generated by `tree-sitter generate`
├── queries/
│   ├── highlights.scm       ← highlight queries (for Neovim, Helix, etc.)
│   ├── injections.scm       ← injection queries (if CALM uses separate grammar)
│   ├── locals.scm           ← local variable scoping
│   └── folds.scm            ← fold regions (macro/if/while/etc. blocks)
├── test/
│   └── corpus/
│       ├── comments.txt
│       ├── strings.txt
│       ├── numbers.txt
│       ├── identifiers.txt
│       ├── labels.txt
│       ├── directives.txt
│       ├── expressions.txt
│       ├── macros.txt
│       ├── calm.txt
│       └── blocks.txt
├── package.json
├── binding.gyp              ← Node.js native binding
├── bindings/
│   ├── node/
│   ├── rust/
│   └── python/
└── Cargo.toml               ← Rust crate for tree-sitter-fasmg
```

---

## 4. Implementation Phases

### Phase 1: Scaffold & core literals
- `tree-sitter init` scaffold
- External scanner: numbers, strings, line continuation
- Grammar: `source_file`, `comment`, `string_literal`, `number_literal`
- Test corpus: comments, strings, numbers (port from `../test_suit/`)
- **Milestone**: `tree-sitter test` passes for all literal forms

### Phase 2: Identifiers & labels
- External scanner: identifier tokenisation (full rules from syntax_notes)
- Grammar: `identifier`, `label_definition`, `special_symbol`
- Test corpus: identifiers (mid-token quotes, `$` disambiguation, `?`,
  dotted names, Unicode, `#` concatenation)
- **Milestone**: all identifier edge cases parse correctly

### Phase 3: Directives & simple statements
- Grammar: `assignment_statement` (all `=`/`:=`/`=:`/`equ`/etc. forms),
  `data_statement` (db/dw/etc.), `instruction_statement` (catch-all)
- Keyword nodes for all directive groups from `spec.py`
- Test corpus: directives, data definitions, assignments
- **Milestone**: single-line statements parse; keywords get distinct nodes

### Phase 4: Block structures
- Grammar: all `if`/`while`/`repeat`/`iterate`/`match`/`namespace`/
  `virtual`/`postpone` blocks with proper `end` matching
- Grammar: `macro_definition`, `struc_definition` with parameter lists
- Macro parameter modifiers: `?`, `*`, `:default`, `&`, `` ` ``
- Test corpus: nested blocks, macro definitions
- **Milestone**: block nesting works; error recovery on unclosed blocks

### Phase 5: Expressions & operators
- Grammar: full expression tree with precedence
- Word operators (`mod`, `and`, `or`, `xor`, `shl`, `shr`, etc.)
- Size override expressions (`byte [x]`, `word [x]`, etc.)
- Test corpus: operator precedence, complex expressions
- **Milestone**: expressions parse with correct precedence

### Phase 6: CALM DSL
- Grammar: `calminstruction_block` with `calm_statement` children
- Individual CALM command rules with their specific argument syntax
- CALM `match` wildcard modifiers as distinct node type
- CALM labels (jump targets)
- Test corpus: CALM blocks with all command types
- **Milestone**: CALM blocks parse distinctly from base language

### Phase 7: Highlight queries & editor integration
- `highlights.scm` mapping node types → highlight groups
- `folds.scm` for all block pairs
- `locals.scm` for label/symbol scoping
- Test against Neovim, Helix, Zed
- **Milestone**: syntax highlighting comparable to TextMate grammar

### Phase 8: Polish & edge cases
- Error recovery tuning (unclosed blocks, invalid numbers, unclosed strings)
- Performance profiling on large fasmg source files
- Binding generation (Node, Rust, Python)
- npm publish preparation
- **Milestone**: production-ready grammar

---

## 5. Key Design Decisions

### 5.1 Single grammar vs. multi-language injection for CALM
**Decision**: single grammar. CALM shares enough with the base language
(strings, numbers, operators, identifiers) that splitting would duplicate
rules. A `calm_block` node with `calm_statement` children is cleaner.

### 5.2 External scanner scope
**Decision**: handle identifiers, numbers, and strings in the external
scanner. These three token types have rules too complex for Tree-sitter's
built-in regex (mid-token quotes, `$` disambiguation, separator rules,
line-based string closing). Comments are simple enough for the grammar DSL.

### 5.3 Case insensitivity
**Decision**: use Tree-sitter's `word` mechanism where possible. For
keywords that must be case-insensitive, define them as `word` tokens and
set the `word` regex to `[a-zA-Z_][a-zA-Z0-9_]*`. For compound keywords
like `end if`, define them as `seq('end', 'if')` so Tree-sitter handles
each word independently.

### 5.4 Context-dependent first-token interpretation
**Decision**: parse structurally. The first non-label token on a line is
tagged as `instruction` in the grammar. Semantic tools can refine this.
The grammar does not attempt multi-pass symbol resolution.

### 5.5 `retaincomments` / `isolatelines` state
**Decision**: ignore these directives in the grammar. They alter fasmg's
tokenisation at runtime, but Tree-sitter is a stateless parser.
`;` is always a comment; `\` at EOL always continues. This matches the
overwhelming default and the expectation of every fasmg source file in
practice.

### 5.6 Symbol stacking is a semantic concern, not a grammar concern

**Decision**: the grammar does **not** attempt to track `define`/`restore`/
`purge`/`restruc` state. Every name gets tagged by its syntactic position
(first on line → potential instruction; after label → potential labeled-
instruction; elsewhere → expression). Whether the name actually has a
meaning in that class is a downstream semantic question.

Verified implications (all against fasmg `g.l4gs`):
- `define db 42; dd db` — `db` resolves as expression (user shadow), not directive.
- `purge` removes instruction class only; `restruc` removes labeled-instruction
  class only; `restore` removes expression class only.
- `reequ`/`redefine` replace the top of stack without pushing.
- `mvmacro`/`mvstruc` rename across instruction/labeled-instruction class.
- Keywords, built-ins, and size constants can all be shadowed and later restored.

The grammar should tag `restore`, `purge`, `restruc` as distinct statement
types (they have unique argument semantics) but need not model the stack.

### 5.7 Assignment syntax has two distinct forms

**Decision**: the grammar must distinguish prefix and infix assignment:

| Form | Syntax | Grammar rule |
|---|---|---|
| **Infix** | `name OP value` | `assignment_statement` with `name`, `operator`, `value` fields |
| **Prefix** | `KEYWORD name value` | `directive_statement` with `keyword`, `arguments` fields |

Infix: `=`, `:=`, `=:`, `equ`, `reequ`
Prefix: `define`, `redefine`, `label`, `element`

The contributed grammar.js already handles this split correctly.

### 5.8 Angle-bracket groups are structural delimiters, not operators

**Decision**: `<` and `>` in argument position are **group delimiters**
(like parentheses), not comparison operators. The contributed grammar
handles this via `angled_argument` nodes with opaque `angled_text_fragment`
content — this is the right approach for now. A future refinement could
parse the interior, but the risk of ambiguity with comparison `<`/`>` in
expressions makes opaque treatment safer.

### 5.9 CALM `match` sigils and bracket pairs need dedicated node types

**Decision**: CALM `match` has up to 4 arguments with complex semantics:
1. Pattern (with wildcards, literal separators, and sigil+modifier annotations)
2. Source identifier
3. Optional bracket pair (`()`, `[]`, `<>`, `{}`) OR sigil character (`:`, `/`, `-`, `.`, etc.)
4. Optional further arguments

The grammar should expose:
- `calm_match_pattern` — the first argument
- `calm_match_source` — the second argument (always an identifier)
- `calm_match_option` — the third argument (bracket pair or sigil)

Wildcard modifiers (`name`, `expression`, `number`, `quoted`, etc.) appear
as `sigil + modifier_name` within the pattern. These can be tagged as
`calm_wildcard_modifier` nodes, but only when a sigil is present (the 3rd
argument determines which character is the sigil).

### 5.10 Leading-comma calls and `outscope` are structural patterns

`_, "file", ico` — leading comma means the first argument is empty.
The grammar handles this via `comma_prefixed_argument_list` (contributed).

`outscope` wraps an entire statement line and evaluates it one scope up.
It should be a distinct node type: `outscope_statement` containing a
child `_simple_statement`.

---

## 6. Semantic Layer Guidance (for downstream consumers)

This section documents what a **semantic analysis layer** (LSP, linter, etc.)
built on top of the parse tree would need to handle. The Tree-sitter grammar
intentionally does not attempt any of this.

### 6.1 Three-class symbol resolution

Every identifier has potentially three meanings (expression, instruction,
labeled-instruction). Resolution depends on:
1. All prior `define`/`equ`/`macro`/`struc`/`calminstruction` definitions
2. All prior `restore`/`purge`/`restruc` removals
3. All prior `mvmacro`/`mvstruc` renames
4. All prior `reequ`/`redefine` replacements
5. Forward references (fasmg is multi-pass — a name can be used before definition)

### 6.2 Stacked meanings and fallback

Each class has an independent stack per name. Built-in meanings (`$`, `byte`, etc.)
are the bottom of the stack and return as fallback after all user definitions are
removed. `restore`/`purge`/`restruc` each peel one layer from their respective class.

### 6.3 Scope boundaries

- `macro`/`struc`/`calminstruction` bodies create new scopes.
- `local` creates scope-local names.
- `outscope` escapes one level.
- `namespace` creates named scope containers.
- `postpone` defers execution to after the current scope ends.

### 6.4 Multi-pass resolution

fasmg resolves forward references by running multiple passes. A name might be
undefined on pass 1 but defined on pass 2. Semantic tools should either:
- Run a simplified multi-pass resolver, or
- Accept that some references will appear "undefined" and suppress false errors.

---

## 7. Testing Strategy (updated)

- **Port existing test suite**: convert `../test_suit/pass/*.g` and
  `../test_suit/fail/*.g` into Tree-sitter corpus format (input +
  expected S-expression).
- **Keyword coverage**: one test per keyword group from `spec.py`.
- **Number edge cases**: all rows from the corner-case tables in
  `fasmg.syntax_notes.md`.
- **Identifier edge cases**: mid-token quotes, `$` forms, `?` prefix/
  suffix, dotted numeric segments, Unicode, `#` concatenation.
- **Symbol stacking**: define/restore/purge sequences, keyword shadowing,
  reequ/redefine replace-top, triple-class coexistence.
- **Assignment forms**: infix (`=`, `:=`, `=:`, `equ`, `reequ`) vs prefix
  (`define`, `redefine`, `label`, `element`).
- **Line position**: label chaining (`a: b: c: db 0`), label + labeled-
  instruction on same line, `outscope` wrapping.
- **Angle-bracket groups**: macro arguments, iterate variable groups, define
  values, match sources.
- **CALM match**: sigil characters, bracket pairs, wildcard modifiers
  (`name`, `expression`, `number`, `quoted`, `equ`, `macro`, `struc`, etc.).
- **Real script forms**: adapted from VSF Example 10 downstream usage —
  `calminstruction (target)`, `else match` chains, leading-comma calls.
- **Error recovery**: unclosed blocks, unclosed strings, invalid numbers
  should produce `ERROR` nodes without cascading.
- **Regression**: CI runs `tree-sitter test` alongside `validate.py`.

---

## 8. Dependencies

- Tree-sitter CLI (`tree-sitter` ≥ 0.24)
- Node.js (for `tree-sitter generate`)
- C compiler (for external scanner)
- Python 3.10+ (for test generation scripts that read `spec.py`)

---

## 9. References

- fasmg documentation: `C:\git\~tgrysztar\fasmg\core\docs\{fasmg,manual}.txt`
- Syntax notes: `../fasmg.syntax_notes.md`
- Spec (single source of truth): `../scripts/spec.py`
- TextMate grammar (reference output): `../fasmg.tmLanguage.json`
- Tree-sitter docs: https://tree-sitter.github.io/tree-sitter/
- Tree-sitter external scanners: https://tree-sitter.github.io/tree-sitter/creating-parsers/4-external-scanners.html
- Upstream assist notes (VSF team): `C:\Z_gpt\vsf\docs\fasmg_syntax_upstream_assist.md`
- Contributed grammar.js and starter queries: this directory
- Test suite (binary-validated): `../test_suit/{pass,fail}/*.g`
