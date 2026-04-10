; Base scope anchors. These are intentionally conservative until the real
; Tree-sitter grammar and semantic layer agree on `fasmg` shadowing rules.

(macro_definition
  name: (identifier) @local.scope)

(calminstruction_definition
  name: (identifier) @local.scope)

(label_definition
  name: (identifier) @local.definition)

(assignment_statement
  name: (identifier) @local.definition)

(parameter
  name: (identifier) @local.definition)

(identifier) @local.reference
