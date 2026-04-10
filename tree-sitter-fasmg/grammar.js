const keywordGroups = require("./keyword-groups.json");
const tokenization = require("./tokenization.json");

const DIRECTIVE_KEYWORDS = [
  ...keywordGroups.controlDirectives.filter(
    (keyword) =>
      !keyword.startsWith("end ")
      && !keyword.startsWith("else")
      && keyword !== "if"
      && keyword !== "end"
      && keyword !== "match"
      && keyword !== "rawmatch"
      && keyword !== "rmatch"
      && keyword !== "while"
      && keyword !== "repeat"
      && keyword !== "rept"
      && keyword !== "iterate"
      && keyword !== "irp"
      && keyword !== "irpv"
      && keyword !== "namespace"
      && keyword !== "virtual"
      && keyword !== "postpone",
  ),
  ...keywordGroups.dataDirectives,
  ...keywordGroups.storageDirectives.filter((keyword) => keyword !== "restore" && keyword !== "purge"),
  ...keywordGroups.otherDirectives,
];

const END_KEYWORDS = keywordGroups.controlDirectives.filter((keyword) => keyword.startsWith("end "));
const BUILT_IN_SYMBOL_PATTERNS = keywordGroups.builtInSymbols.map((pattern) => new RegExp(pattern, "i"));
const WORD_OPERATOR_KEYWORDS = [...keywordGroups.wordOperators, ...keywordGroups.calmMatchModifiers];
const NUMBER_PATTERNS = [
  /0x[0-9A-Fa-f_']+/,
  /\$[0-9A-Fa-f][0-9A-Fa-f_']*/,
  /[0-9][0-9A-Fa-f_']*[hH]/,
  /[01][01_']*[bB]/,
  /[0-7][0-7_']*[oOqQ]/,
  /[0-9][0-9_']*\.[0-9][0-9_']*(?:[eE][+-]?[0-9_']*[0-9][0-9_']*|[fF])?/,
  /[0-9][0-9_']*[eE][+-]?[0-9_']*[0-9][0-9_']*/,
  /[0-9][0-9_']*[fF]/,
  /[0-9][0-9_']*[dD]?/,
];

function escapeRegex(text) {
  return text.replace(/[|\\{}()[\]^$+*?.-]/g, "\\$&");
}

function ciWord(word) {
  const pattern = word
    .split("")
    .map((character) => {
      if (/[A-Za-z]/.test(character)) {
        return `[${character.toLowerCase()}${character.toUpperCase()}]`;
      }

      return escapeRegex(character);
    })
    .join("");

  return new RegExp(pattern);
}

function ciPhrase(phrase) {
  return seq(...phrase.split(/\s+/).map((word) => keywordToken(word)));
}

function keywordToken(word) {
  return token(prec(1, ciWord(word)));
}

function keywordRule(keyword) {
  return keyword.includes(" ") ? ciPhrase(keyword) : keywordToken(keyword);
}

module.exports = grammar({
  name: "fasmg",

  word: ($) => $.identifier,

  extras: ($) => [/[ \t\r]+/, $.line_continuation, $.comment],

  rules: {
    source_file: ($) => repeat(choice($._statement, $._blank_line)),

    _blank_line: () => /\n+/,

    _statement: ($) =>
      seq(
        choice(
          $.macro_definition,
          $.struc_definition,
          $.calminstruction_definition,
          $.if_block,
          $.match_block,
          $.while_block,
          $.repeat_block,
          $.iterate_block,
          $.irp_block,
          $.namespace_block,
          $.virtual_block,
          $.postpone_block,
          $.labeled_statement,
          $._simple_statement,
        ),
        optional(/\n/),
      ),

    _simple_statement: ($) =>
      choice(
        $.restore_statement,
        $.purge_statement,
        $.assignment_statement,
        $.directive_statement,
        $.instruction_statement,
      ),

    labeled_statement: ($) =>
      prec.right(seq(
        $.label_definition,
        optional($._simple_statement),
      )),

    block_body: ($) =>
      prec.right(
        repeat1(
        choice(
          $._statement,
          $._blank_line,
        ),
        ),
      ),

    comment: () => token(seq(";", /.*/)),

    line_continuation: () => token(seq("\\", /\r?\n/)),

    identifier: () =>
      token(
        prec(
          -1,
        choice(
          /\.[^\s+\-/*=<>()\[\]{}:?!,.|&~'"`;\\#][^\s+\-/*=<>()\[\]{}:?!,.|&~`;\\#]*/,
          /\?[^\s0-9+\-/*=<>()\[\]{}:?!,.|&~'"`;\\#][^\s+\-/*=<>()\[\]{}:?!,.|&~`;\\#]*/,
          /[^\s0-9+\-/*=<>()\[\]{}:?!,.|&~'"`;\\][^\s+\-/*=<>()\[\]{}:?!,.|&~`;\\#]*/,
        ),
        ),
      ),

    string_literal: () =>
      token(
        prec(
          2,
        choice(
          /'([^'\n]|'')*'/,
          /"([^"\n]|"")*"/,
        ),
        ),
      ),

    number_literal: () => token(prec(2, choice(...NUMBER_PATTERNS))),

    label_definition: ($) =>
      seq(
        field("name", $.identifier),
        field("operator", choice(token.immediate("::"), token.immediate(":"))),
      ),

    parameter_list: ($) => seq($.parameter, repeat(seq(",", $.parameter))),

    parameter: ($) =>
      seq(
        field("name", $.identifier),
        optional(choice("?", "*")),
        optional(seq(":", field("default", $.argument))),
      ),

    argument_list: ($) => seq($.argument, repeat(seq(",", $.argument))),

    argument: ($) =>
      choice(
        $.angled_argument,
        prec.right(repeat1($.argument_atom)),
      ),

    instruction_argument_list: ($) =>
      seq(
        $.instruction_argument,
        repeat(seq(",", $.argument)),
      ),

    instruction_argument: ($) =>
      choice(
        $.angled_argument,
        prec.right(
          seq(
            $.instruction_argument_head,
            repeat($.argument_atom),
          ),
        ),
      ),

    instruction_argument_head: ($) =>
      choice(
        $.number_literal,
        $.string_literal,
        $.built_in_symbol,
        $.sigil_token,
        $.word_operator,
        $.identifier,
        $.parenthesized_argument,
        $.bracketed_argument,
        $.braced_argument,
      ),

    argument_atom: ($) =>
      choice(
        $.number_literal,
        $.string_literal,
        $.built_in_symbol,
        $.sigil_token,
        $.word_operator,
        $.identifier,
        $.operator_token,
        $.parenthesized_argument,
        $.bracketed_argument,
        $.braced_argument,
      ),

    built_in_symbol: () => token(prec(3, choice(...BUILT_IN_SYMBOL_PATTERNS))),

    sigil_token: () =>
      token(
        prec(
          3,
          choice(
            /=:[^\s,)\]}>]+/,
            /=[A-Za-z_.?$%][^\s,)\]}>]*/,
            /`[^\s,)\]}>]+/,
            /:[A-Za-z_.?$%][^\s,)\]}>]*/,
          ),
        ),
      ),

    word_operator: () => prec.right(choice(...WORD_OPERATOR_KEYWORDS.map((keyword) => keywordRule(keyword)))),

    operator_token: () =>
      token(
        prec(
          -1,
          choice(
            ":==",
            "<>",
            "<=",
            ">=",
            "<<",
            ">>",
            "+",
            "-",
            "*",
            "/",
            "=",
            "<",
            ">",
            "&",
            "|",
            "~",
            "!",
            "?",
            ".",
            ":",
            "#",
          ),
        ),
      ),

    angled_argument: ($) =>
      prec(
        2,
        seq(
          "<",
          repeat(choice($.line_continuation, $.angled_text_fragment)),
          ">",
        ),
      ),

    angled_text_fragment: () => token(prec(1, /[^>\r\n\\]+/)),

    parenthesized_argument: ($) => seq("(", optional($.argument_list), ")"),

    bracketed_argument: ($) => seq("[", optional($.argument_list), "]"),

    braced_argument: ($) => seq("{", optional($.argument_list), "}"),

    match_pattern: ($) => $.argument_list,

    _expression: ($) =>
      choice(
        $.number_literal,
        $.string_literal,
        $.identifier,
        seq("(", $._expression, ")"),
      ),

    assignment_statement: ($) =>
      prec.right(2,
        seq(
        field("name", $.identifier),
        field("operator", choice("=", ":=", "=:", "equ", "reequ", "define", "redefine")),
        optional(field("value", $.argument_list)),
        ),
      ),

    restore_statement: ($) => seq(keywordToken("restore"), field("name", $.identifier)),

    purge_statement: ($) => seq(keywordToken("purge"), field("name", $.identifier)),

    directive_keyword: () => prec.right(choice(...DIRECTIVE_KEYWORDS.map((keyword) => keywordRule(keyword)))),

    directive_statement: ($) =>
      prec.right(
        seq(
        field("keyword", $.directive_keyword),
        optional(field("arguments", $.argument_list)),
        ),
      ),

    instruction_statement: ($) =>
      prec.right(-1,
        choice(
          seq(
            field("name", $.identifier),
            field("arguments", $.comma_prefixed_argument_list),
          ),
          seq(
            field("name", $.identifier),
            optional(field("arguments", $.instruction_argument_list)),
          ),
        ),
      ),

    comma_prefixed_argument_list: ($) => seq(",", $.argument_list),

    end_clause: () => choice(...END_KEYWORDS.map((keyword) => keywordRule(keyword))),

    macro_definition: ($) =>
      seq(
        keywordToken("macro"),
        optional("!"),
        field("name", $.identifier),
        optional(choice("?", "!")),
        optional(field("parameters", $.parameter_list)),
        /\n/,
        field("body", $.block_body),
        field("end", ciPhrase("end macro")),
      ),

    struc_definition: ($) =>
      seq(
        keywordToken("struc"),
        optional("!"),
        field("name", $.identifier),
        optional(choice("?", "!")),
        optional(field("parameters", $.parameter_list)),
        /\n/,
        field("body", $.block_body),
        field("end", ciPhrase("end struc")),
      ),

    calminstruction_definition: ($) =>
      seq(
        keywordToken("calminstruction"),
        optional("!"),
        choice(
          seq(
            field("target", $.calm_target),
            field("name", $.identifier),
          ),
          field("name", $.identifier),
        ),
        optional(choice("?", "!")),
        optional(field("parameters", $.parameter_list)),
        /\n/,
        field("body", $.block_body),
        field("end", ciPhrase("end calminstruction")),
      ),

    calm_target: ($) => seq("(", $.identifier, ")"),

    if_block: ($) =>
      seq(
        keywordToken("if"),
        field("condition", $.argument_list),
        /\n/,
        field("body", $.block_body),
        repeat(field("else_if_clauses", $.else_if_clause)),
        optional(field("else_clause", $.else_clause)),
        field("end", ciPhrase("end if")),
      ),

    else_if_clause: ($) =>
      seq(
        keywordToken("else"),
        keywordToken("if"),
        field("condition", $.argument_list),
        /\n/,
        field("body", $.block_body),
      ),

    else_clause: ($) =>
      seq(
        keywordToken("else"),
        /\n/,
        field("body", $.block_body),
      ),

    while_block: ($) =>
      seq(
        keywordToken("while"),
        optional(field("condition", $.argument_list)),
        /\n/,
        field("body", $.block_body),
        field("end", ciPhrase("end while")),
      ),

    repeat_block: ($) =>
      seq(
        choice(keywordToken("repeat"), keywordToken("rept")),
        optional(field("arguments", $.argument_list)),
        /\n/,
        field("body", $.block_body),
        field("end", ciPhrase("end repeat")),
      ),

    iterate_block: ($) =>
      seq(
        keywordToken("iterate"),
        optional(field("arguments", $.argument_list)),
        /\n/,
        field("body", $.block_body),
        field("end", ciPhrase("end iterate")),
      ),

    irp_block: ($) =>
      seq(
        choice(keywordToken("irp"), keywordToken("irpv")),
        optional(field("arguments", $.argument_list)),
        /\n/,
        field("body", $.block_body),
        field("end", choice(ciPhrase("end irp"), ciPhrase("end irpv"))),
      ),

    namespace_block: ($) =>
      seq(
        keywordToken("namespace"),
        optional(field("arguments", $.argument_list)),
        /\n/,
        field("body", $.block_body),
        field("end", ciPhrase("end namespace")),
      ),

    virtual_block: ($) =>
      seq(
        keywordToken("virtual"),
        optional(field("arguments", $.argument_list)),
        /\n/,
        field("body", $.block_body),
        field("end", ciPhrase("end virtual")),
      ),

    postpone_block: ($) =>
      seq(
        keywordToken("postpone"),
        optional(field("arguments", $.argument_list)),
        /\n/,
        field("body", $.block_body),
        field("end", ciPhrase("end postpone")),
      ),

    match_block: ($) =>
      seq(
        choice(keywordToken("match"), keywordToken("rawmatch"), keywordToken("rmatch")),
        optional(field("pattern", $.match_pattern)),
        /\n/,
        field("body", $.block_body),
        repeat(field("else_match_clauses", $.else_match_clause)),
        optional(field("else_clause", $.else_clause)),
        field("end", ciPhrase("end match")),
      ),

    else_match_clause: ($) =>
      seq(
        keywordToken("else"),
        keywordToken("match"),
        field("pattern", $.match_pattern),
        /\n/,
        field("body", $.block_body),
      ),
  },
});
