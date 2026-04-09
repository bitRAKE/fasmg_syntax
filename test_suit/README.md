# fasmg test suite

Fixtures for exercising `fasmg.tmLanguage.json` and, optionally, the real
`fasmg` assembler.

- `pass/` — source files that are **valid** fasmg. The assembler should accept
  them with no errors, and the grammar should tokenize them without producing
  any `invalid.illegal.*` scopes.
- `fail/` — source files that are **invalid**. The assembler should reject
  them, and where the failure is a syntactic one the grammar should surface
  an `invalid.illegal.*` scope.

## Naming

`<short_description>.<fasmg-version>.g`

- `<fasmg-version>` tracks the oldest fasmg version the test is known to
  apply to. fasmg does **not** use semver — it prints a freeform token after
  `flat assembler  version g.` (e.g. `l4gs`). Use that token verbatim.
- When language behaviour changes in a later release, add a new file rather
  than editing an existing one — the old one documents the previous
  behaviour, and the suffix makes it clear which version it targets.
- The binary currently lives at
  `C:\git\~tgrysztar\fasmg\core\fasmg.exe`, reporting version `l4gs`.

## Running

See `../scripts/validate.py` (once added). The script should:

1. Assemble every `pass/*.g` and assert exit code 0.
2. Assemble every `fail/*.g` and assert exit code ≠ 0.
3. Optionally tokenize with a TextMate engine (e.g. `vscode-textmate`) and
   check that `pass/` produces no `invalid.*` scopes, while each `fail/` file
   with a matching `.expect` sidecar produces the listed scope.
