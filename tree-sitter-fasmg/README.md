
## What Is Included

- `grammar.js`
  - the current working grammar draft from the VSF Example 10 Tree-sitter workspace
- `keyword-groups.json`
  - the keyword snapshot the grammar currently imports
- `tokenization.json`
  - the token-shape snapshot the grammar currently imports
- `queries/*.scm`
  - starter highlight, locals, and folds queries

## What This Grammar Already Covers

The handed-off grammar currently parses these useful forms:

- `calminstruction (target) Name ...`
- `else match ...`
- angle-bracket grouped arguments such as `<IndexForm Q,S,I>`
- leading-comma instruction calls such as `_, "file name: ", ico`
- label-plus-instruction same-line forms
- block structures such as `while`, `repeat`, `iterate`, `irp`, `namespace`, `virtual`, and `postpone`

## What Is Probably Reusable

- the grammar rule structure
- the current block and statement shapes
- the syntax slices captured in `real-script-forms.txt`
- the starter queries as rough placeholders

## Important Notes

- This grammar is still a draft, not a final upstream `tree-sitter-fasmg` design.
- It currently uses `*.json` snapshots instead of deriving everything directly from `spec.py`.
- Angle-bracket groups are currently treated conservatively as bounded opaque nodes (`angled_argument` with `angled_text_fragment`) to avoid destabilizing comparison parsing before the semantic layer is stronger.

## Suggested Use

1. Review `grammar.js` for rule shapes worth adopting.
2. Cherry-pick or rewrite the relevant forms into the main grammar design.
3. Keep or discard the `*.json` snapshot approach depending on how tightly you want to couple the grammar to `spec.py`.
