full_definition = r"""
comment = ('#' {(~'\n' {anything})*})=comment
hspaces = (' ' | '\t' | escaped_linebreak)*
hspacesp = (' ' | '\t' | escaped_linebreak)+
escaped_linebreak = '\\' {'\n'}

single_input = EMPTY_LINE | simple_stmt | (compound_stmt EMPTY_LINE)
file_input = (EMPTY_LINE | SAME_INDENT stmt)* ENDMARKER
eval_input = testlist NEWLINE? EMPTY_LINE* ENDMARKER

decorator! = "@" {dotted_name ("(" {arglist} ")")?} NEWLINE
decorators! = decorator+
decorated = decorators (classdef | funcdef)
funcdef = "def" {NAME} "(" {parameters | void=parameters} ")" ":" {suite}
# Check order validity elsewhere (at most one remaining_args and one kwargs)
parameters! = {fpdef_opt (comma {fpdef_opt})*} comma?

fpdef = NAME | "(" fplist ")"
fpdef_opt = fpdef ("=" {test})? | "*" {NAME=remaining_args} | "**" {NAME=kwargs}
fplist = {fpdef (comma {fpdef})*} comma?

stmt = compound_stmt | simple_stmt
simple_stmt = {small_stmt (";" {small_stmt})*} ";"? NEWLINE
small_stmt = print_stmt | del_stmt | pass_stmt | flow_stmt | comment
           | import_stmt | global_stmt | exec_stmt | assert_stmt | expr_stmt

expr_stmt = aug_assign | regular_assign | testlist
aug_assign_symbol = "+=" | "-=" | "*=" | "/=" | "%=" | "&="
                  | "|=" | "^=" | "<<=" | ">>=" | "**=" | "//="
aug_assign = testlist aug_assign_symbol=operation (yield_expr|testlist)
regular_assign = testlist ("=" {yield_expr|testlist})+
# For normal assignments, additional restrictions enforced by the interpreter
print_stmt! = "print" { {test ("," {test})*} ","?
                      | ">>" test ( ("," test)+ ","? )? | void}
del_stmt! = "del" hspacesp {exprlist}
pass_stmt! = "pass" {}
flow_stmt = break_stmt | continue_stmt | return_stmt | raise_stmt | yield_stmt
break_stmt! = "break" {}
continue_stmt! = "continue" {}
return_stmt! = "return" {testlist?}
yield_stmt = yield_expr
raise_stmt! = "raise" {(test ("," test ("," test))?)?}
import_stmt = simport_stmt | import_name | import_from
simport_stmt! = "simport" {NAME}
import_name = "import" {import_names}
import_names! = dotted_as_name ("," {dotted_as_name})*
import_from! = "from" {"."* dotted_name | "."+}
               "import" {"*"=import_all | "(" {import_as_names} ")" | import_as_names}
import_as_name = NAME ("as" {NAME})?
dotted_as_name = dotted_name ("as" {NAME})?
import_as_names! = {import_as_name ("," {import_as_name})*} ","?
dotted_name = NAME ("." {NAME})*
global_stmt = "global" NAME ("," NAME)*
exec_stmt! = "exec" {expr ("in" {test} ("," {test})?)?}
assert_stmt! = "assert" {test ("," test)?}

compound_stmt = if_stmt | while_true_stmt=while_true | while_stmt
              | simple_for_stmt | for_stmt | try_stmt | with_stmt
              | funcdef | classdef | decorated
if_stmt = ("if" {test} ":" {suite})=single_if
          ((SAME_INDENT "elif" {test} ":" {suite})=single_if)*
          ((SAME_INDENT "else" ":" {void=gen_true suite})=single_if)?
while_true_stmt = "while_true" ":" {suite}
while_stmt = "while" {test} ":" {suite (SAME_INDENT "else" ":" {suite})?}
for_stmt = "for" {exprlist} "in" {testlist} ":" {suite} {(SAME_INDENT "else" ":" {suite})?}
simple_for_stmt = "simple_for" {exprlist} "in" {testlist} ":" {suite}
try_stmt! = "try" ":" {suite}
            {((SAME_INDENT {exception} ":" {suite})=except_clause)+=except_clauses
             (SAME_INDENT  "else" ":" suite)?
             (SAME_INDENT "finally" ":" suite)?
             | SAME_INDENT "finally" ":" suite}
with_stmt = "with" with_item ("," with_item)* ":" suite
with_item = test ("as" expr)?
# NB compile.c makes sure that the default except clause is last
exception! = "except" {(test (("as" | ",") {test})?)?}
# Should "give back" the consumed empty lines at the end!
suite = NEWLINE INDENT {(SAME_INDENT stmt | EMPTY_LINE)+} DEDENT
      | simple_stmt

testlist = {test ("," {test})*} ","?
yield_expr! = "yield" {testlist?}

test = lambdef | or_test ("if" {or_test} {("else" {test})?})?
or_test = and_test ("or" {and_test})*
and_test = not_test ("and" {not_test})*
not_test = ("not" {not_test})=not_test | comparison

comparison = factor:start (hspaces {?(any_token(self.input))}
                           hspaces {factor})*:oper_and_atoms
             -> reformat_binary(start, oper_and_atoms)
expr = factor:start (hspaces {?(any_token(self.input, binary=False))}
                     hspaces {factor})*:oper_and_atoms
     -> reformat_binary(start, oper_and_atoms)

factor = ("+"|"-"|"~")* power
power = trailed_atom ("**" factor)?
trailed_atom = atom:atom trailer*:trailers -> reformat_atom(atom, trailers)
atom = "(" spaces {parenthesis} spaces ")"
     | "[" spaces {listmaker | void=listmaker} spaces "]"
     | "{" spaces {dictmaker} spaces "}"
     | "{" {setmaker} spaces "}"
     | "`" {(stmt | small_stmt)=thunk} "`"
     | STRINGS | NAME | NUMBER
parenthesis = yield_expr | testlist_comp=generator | tuple 
            | test | void=no_param
listmaker! = (test list_for list_iter*)=listcomp
           | {test (comma {test})*} comma?
testlist_comp = test list_for list_iter*
tuple! = ({test} comma)+ test?
lambdef! = "lambda" {parameters? | void=parameters} ":" {test}
trailer = "(" spaces {arglist} spaces ")"
        | "[" spaces {subscriptlist=subscriptlist} spaces "]"
        | "." {NAME}
subscriptlist! = subscript ("," {subscript})* ","?
subscript! = "..."=ellipsis | ({test?=start} ":" {test?=stop} {step?})=slice | test
exprlist = {expr ("," {expr})*} ","?
step! = ":" {test?}
dictmaker! = ({test} ":" {test} {list_for} {list_iter*})=dictcomp
           | {({test} ":" {test})=pair ((comma {test} ":" {test})=pair)*} comma?
           | void

setmaker! = test (list_for list_iter* | (("," test)* ","?))

classdef = "class" {NAME} {("(" {testlist?} ")")?=parents} ":" {suite}

arglist! = ({argument} comma)* ( "**" {test=kwargs}
                               | "*" {test=remaining_args ("," keyword_arg)* ("," "**" {test=kwargs})?}
                               | {argument | void} )
                       comma?

comma = "," spaces

argument = keyword_arg | listcomp_arg
keyword_arg = {test} "=" {test}
listcomp_arg = test (list_for list_iter*)?

list_iter = list_for | list_if
list_for = spaces "for" {exprlist} "in" {or_test} # {testlist_safe}
list_if! = spaces "if" {or_test}

testlist_safe = or_test ((',' or_test)+ ','?)?
testlist1 = test ("," test)*

NUMBER! = hspaces digit+:s -> int("".join(n[0] for n in s))
# Probably need to check that the result isn't a reserved word.
NAME! = hspaces {((letter | '_') (letter | digit | '_')*)}
STRINGS = {STRING | RAW_STRING=STRING} (spaces {STRING | RAW_STRING=STRING})*
STRING! = hspaces stype? '"' '"' '"' {(escaped_char | ~('"' '"' '"') {anything})*} '"' '"' '"'
       | hspaces stype? '\'' {(escaped_char | ~'\'' anything)*} '\''
       | hspaces stype? '"' {(escaped_char | ~'"' anything)*} '"'
RAW_STRING = hspaces 'r' '"' '"' '"' {(~('"' '"' '"') {anything})*} '"' '"' '"'
           | hspaces 'r' '\'' {(~'\'' anything)*} '\''
           | hspaces 'r' '"' {(~'"' anything)*} '"'
stype! = 'b'
escaped_char! = '\\' {'n'|'r'|'t'|'b'|'f'|'"'|'\''|'\\'}
EMPTY_LINE = (hspaces comment? ('\n' | '\r'))=EMPTY_LINE
NEWLINE = hspaces (comment hspaces)? ('\n' | '\r')
SAME_INDENT = hspaces:s ?(self.indentation[-1] == (len(s) if s != None else 0))
ENDMARKER = ~anything
INDENT = ~~hspaces:s !(self.indentation.append(len(s) if s != None else 0))
DEDENT = !(self.indentation.pop())

grammar = file_input
"""

extra = """
letter = 'a'|'b'|'c'|'d'|'e'|'f'|'g'|'h'|'i'|'j'|'k'|'l'|'m'|'n'|'o'|'p'|'q'|'r'|'s'|'t'|'u'|'v'|'w'|'x'|'y'|'z'|'A'|'B'|'C'|'D'|'E'|'F'|'G'|'H'|'I'|'J'|'K'|'L'|'M'|'N'|'O'|'P'|'Q'|'R'|'S'|'T'|'U'|'V'|'W'|'X'|'Y'|'Z'
digit = '0'|'1'|'2'|'3'|'4'|'5'|'6'|'7'|'8'|'9'
space = '\t'|'\n'|'\r'|' '|comment
spaces = space*
"""
