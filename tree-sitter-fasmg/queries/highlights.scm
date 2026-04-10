; Core lexical captures.
(comment) @comment
(string_literal) @string
(number_literal) @number

; Named syntax nodes that already line up with the Example 10 parser contracts.
(label_definition
  name: (identifier) @label)

(macro_definition
  name: (identifier) @function.macro)

(calminstruction_definition
  name: (identifier) @function.special)

(parameter
  name: (identifier) @parameter)

; Directive-heavy statements are intentionally broad in the scaffold phase.
(directive_statement
  keyword: (directive_keyword) @keyword.directive)

(restore_statement) @keyword.directive
(purge_statement) @keyword.directive
