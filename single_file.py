NAME, FLAGS, ARGS, BODY = [0, 1, 2, 3]
inf = float("inf")

class MatchError(Exception):
    pass

class Node(list):
    def __init__(self, name=None, value=None):
        list.__init__(self, value if value is not None else [])
        self.name = name

    def __repr__(self):
        return "%s%s" % (self.name, list.__repr__(self))

    def pprint(self, indent=0):
        print " "*indent + self.name
        for child in self:
            if not hasattr(child, "pprint"):
                print " "*(indent + 1), type(child).__name__, repr(child)
            else:
                child.pprint(indent + 2)

def simple_wrap_tree(root):
    if type(root) != list:
        return root
    return Node(root[0], map(simple_wrap_tree, root[1:]))

def pop(input):
    input[1] += 1
    try:
        return input[0][input[1]]
    except IndexError:
        raise MatchError("EOF")

def to_list(output):
    return output  if getattr(output, "name", None) == "And" else\
           []      if output is None else\
           [output]

def to_node(outputs):
    outputs = [elem for output in outputs for elem in to_list(output)]
    return outputs[0]       if len(outputs) == 1 else\
           None             if len(outputs) == 0 else\
           "".join(outputs) if all(type(output) == str for output in outputs)\
           else Node("And", outputs)

class Interpreter:
    def __init__(self, grammar_tree, whitespace="\t\n\r \\"):
        self.rules = {rule[NAME][0]:rule for rule in grammar_tree}
        self.whitespace = whitespace

    def eval(self, root):
        self.locals['self'] = self
        output = eval(root, globals(), self.locals)
        del self.locals['self']
        return output

    def match(self, root, new_input=None, new_pos=-1):
        """ >>> g.match(g.rules['grammar'][-1], "x='y'") """
        if new_input is not None:
            self.input = [new_input, new_pos]
            self.indentation = [0]
            self.locals = {}
        old_input = self.input[:]
        name = root.name
        if name in ["and", "args", "output"]:
            outputs = [self.match(child) for child in root]
            if any(child.name == "output" for child in root):
                outputs = [output for child, output in zip(root, outputs)
                           if child.name == "output"]
            elif any(child.name == "rule_value" for child in root):
                outputs = [output for child, output in zip(root, outputs)
                           if child.name == "rule_value"]
                assert(len(outputs) == 1)
        elif name == "quantified":
            assert(root[1].name == "quantifier")
            lower, upper = {"*": (0, inf), "+": (1, inf), "?": (0, 1)}[root[1][0]]
            outputs = []
            while len(outputs) < upper:
                last_input = self.input[:]
                try:
                    outputs.append(self.match(root[0]))
                except MatchError:
                    self.input = last_input[:]
                    break
            if lower > len(outputs):
                raise MatchError("Matched %s < %s times" % (len(outputs), lower))
        elif name == "or":
            for child in root:
                try:
                    return self.match(child)
                except MatchError:
                    self.input = old_input[:]
            raise MatchError("All Or matches failed")
        elif name in ["exactly", "token"]:
            if name == "token":
                while pop(self.input) in self.whitespace:
                    if self.input[0][self.input[1]] == '\\':
                        pop(self.input)
                self.input[1] -= 1
            for char in root[0]:
                if pop(self.input) != char:
                    raise MatchError("Not exactly %s" % root[0])
            if name == "token" and root[0].isalpha():
                top = pop(self.input)
                if top.isalnum() or top == '_':
                    raise MatchError("Prefix matched but didn't end.")
                self.input[1] -= 1
            return root[0]
        elif name == "apply":
            #import inspect
            #print " "*(len(inspect.stack())-9), "matching", name, root[NAME], self.input[1], self.input[0][self.input[1]+1:self.input[1]+11]
            if root[NAME] == "anything":
                return pop(self.input)
            elif root[NAME] == "void":
                return
            old_locals = self.locals
            self.locals = {}
            try:
                outputs = self.match(self.rules[root[NAME]][BODY])
            finally:
                self.locals = old_locals
            if root[NAME] == "escaped_char":
                chars = dict(["''", '""', "t\t", "n\n", "r\r", "b\b", "f\f", "\\\\"])
                return chars[outputs[-1]]
            and_node = getattr(outputs, "name", None) == "And"
            make_node = "!" in self.rules[root[NAME]][FLAGS] or\
                        (and_node and len(outputs) > 1)
            if not make_node:
                return outputs
            return Node(root[NAME], to_list(outputs))
        elif name in "bound":
            if root[1].name == "inline":
                return Node(root[1][0], to_list(self.match(root[0])))
            else: # bind
                self.locals[root[1][0]] = self.match(root[0])
                return
        elif name == "negation":
            try:
                self.match(root[0])
            except MatchError:
                self.input = old_input
                return None
            raise MatchError("Negation true")
        elif name == "rule_value":
            return self.eval(root[0])
        elif name == "predicate":
            output = self.eval(root[0])
            if not output:
                raise MatchError("Predicate evaluates to false")
            return None if output == True else Node("predicate", [output])
        elif name == "action":
            self.locals['self'] = self
            exec(root[0], globals(), self.locals)
            del self.locals['self']
            return
        elif name == "lookahead":
            output = self.match(root[0])
            self.input = old_input[:]
            return output
        else:
            raise Exception("Unknown operator %s" % name)
        return to_node(outputs)

def reformat_atom(atom, trailers):
    output = atom
    for trailer in to_list(trailers):
        if trailer.name == "arglist":
            output = Node("__call__", [output, trailer])
        elif trailer.name == "NAME":
            output = Node("__getattr__", [output, Node("NAME", trailer)])
        elif trailer.name == "subscriptlist":
            output = Node("__getitem__", [output] + trailer)
        else:
            raise Exception("Unknown trailer %s" % trailer.name)
    return output

binary_ops = ((">=", "<=", "<>", "<", ">", "==", "!=",
               "in", "not in", "is not", "is"),
              ("|",), ("^",), ("&",), ("<<", ">>"), ("+", "-"),
              ("*", "/", "%", "//"), ("**",))
priority = {op:i for i, ops in enumerate(binary_ops) for op in ops}
expr_ops = binary_ops[1:]

def reformat_binary(start, tokens):
    def parse(lhs, tokens, index=0):
        threshold = priority[tokens[index][0][0]]
        while index < len(tokens):
            op, rhs = tokens[index]
            op = op[0]
            if priority[op] < threshold:
                break
            index += 1
            while index < len(tokens) and\
                  priority[tokens[index][0][0]] > priority[op]:
                rhs, index = parse(rhs, tokens, index)
            lhs = Node("__binary__", [op, lhs, rhs])
        return (lhs, index)
    tokens = zip(oper_and_atoms[::2], oper_and_atoms[1::2])
    lhs, index = start, 0
    while index < len(tokens):
        lhs, index = parse(lhs, tokens, index)
    return lhs

def any_token(input, binary=True):
    ops = binary_ops if binary else expr_ops
    old_input = input[:]
    for tokens in ops:
        for token in tokens:
            if all(pop(input) == char for char in token):
                return token
            input[:] = old_input[:]
    return False

grammar = r"""
expr = apply | exactly | token | parenthesis | output | list
     | rule_value | predicate | action

exactly! = "'" {(escaped_char | ~'\'' anything)*} "'"
token! = "\"" {(escaped_char | ~'"' anything)*} "\""
apply! = indentation? {name ('(' {balanced=args} ')')?}
parenthesis = "(" {or} ")"
output! = "{" {or} "}"
list! = "[" {or} "]"
predicate! = "?(" {balanced} ')'
action! = "!(" {balanced} ')'
rule_value! = "->" hspaces {(escaped_char | ~'\n' anything)*}

not = "~" "~" {expr=lookahead} | "~" {expr=negation} | expr
quantified = not (('*' | '+' | '?')=quantifier)?
bound = ":" {name=bind}
      | quantified (':' {name=bind} | '=' {name=inline})?
and = bound*
or = and ("|" {and})*

rule = spaces {name=rule_name '!'?=flags and=args ("=" {or})}
grammar = {rule*} spaces

comment = '#' (~'\n' anything)*
indentation = (hspaces ('\r' '\n' | '\r' | '\n'))* hspacesp
name = (letter | '_') (letter | digit | '_')*
balanced = (escaped_char | '(' balanced ')' | ~')' anything)*
"""

python_grammar = r"""
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
import_stmt = import_name | import_from
import_name = "import" {import_names}
import_names! = dotted_as_name ("," {dotted_as_name})*
import_from! = "from" {"."* dotted_name | "."+}
               "import" {"*" | "(" {import_as_names} ")" | import_as_names}
import_as_name = NAME ("as" {NAME})?
dotted_as_name = dotted_name ("as" {NAME})?
import_as_names! = {import_as_name ("," {import_as_name})*} ","?
dotted_name = NAME ("." {NAME})*
global_stmt = "global" NAME ("," NAME)*
exec_stmt! = "exec" {expr ("in" {test} ("," {test})?)?}
assert_stmt! = "assert" {test ("," test)?}

compound_stmt = if_stmt | while_stmt | for_stmt | try_stmt | with_stmt
              | funcdef | classdef | decorated
if_stmt = ("if" {test} ":" {suite})=single_if 
          (("elif" {test} ":" {suite})=single_if)*
          (("else" ":" {void=gen_true suite})=single_if)?
while_stmt = "while" {test} ":" {suite ("else" ":" {suite})?}
for_stmt = "for" {exprlist} "in" {testlist} ":" {suite} {{"else"} ":" {suite=elseblock}}?
try_stmt! = "try" ":" {suite}
            {(({exception} ":" {suite})=except_clause)+=except_clauses
             ("else" ":" suite)?
             ("finally" ":" suite)?
             | "finally" ":" suite}
with_stmt = "with" with_item ("," with_item)* ":" suite
with_item = test ("as" expr)?
exception! = "except" {(test (("as" | ",") {test})?)?}
suite = NEWLINE INDENT {(SAME_INDENT stmt | EMPTY_LINE)+} DEDENT | simple_stmt

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
        | "[" spaces {subscriptlist} spaces "]"
        | "." {NAME}
subscriptlist! = subscript=subscript ("," subscript=subscript)* ","?
subscript = "..." | ({test?=start} ":" {test?=stop} {step?})=slice | test
exprlist = {expr ("," {expr})*} ","?
step! = ":" {test?}
dictmaker! = ({test} ":" {test} {list_for} {list_iter*})=dictcomp
           | {({test} ":" {test})=pair ((comma {test} ":" {test})=pair)*} comma?
           | void

setmaker! = test (list_for list_iter* | (("," test)* ","?))

classdef = "class" {NAME} {("(" {testlist?} ")")?=parents} ":" {suite}

arglist! = ({argument} comma)* ( "**" {test=kwargs}
                               | "*" {test=remaining_args ("," keyword_arg)* 
                                      ("," "**" {test=kwargs})?}
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

comment! = '#' {(~'\n' {anything})*}
NUMBER! = hspaces digit+:s -> int("".join(n[0] for n in s))
# Probably need to check that the result isn't a reserved word.
NAME! = hspaces {((letter | '_') (letter | digit | '_')*)}
STRINGS = STRING (spaces {STRING})*
STRING! = hspaces stype? '"' '"' '"' {(escaped_char | ~('"' '"' '"') {anything})*} '"' '"' '"'
       | hspaces stype? '\'' {(escaped_char | ~'\'' anything)*} '\''
       | hspaces stype? '"' {(escaped_char | ~'"' anything)*} '"'
stype! = 'r'|'b'
EMPTY_LINE = (hspaces comment? ('\n' | '\r'))=EMPTY_LINE
NEWLINE = hspaces (comment hspaces)? ('\n' | '\r')
SAME_INDENT = hspaces:s ?(self.indentation[-1] == (len(s) if s else 0))
ENDMARKER = ~anything
INDENT = ~~hspaces:s !(self.indentation.append(len(s) if s else 0))
DEDENT = !(self.indentation.pop())
"""

extra = r"""
escaped_char! = '\\' {'n'|'r'|'t'|'b'|'f'|'"'|'\''|'\\'}
letter = 'a'|'b'|'c'|'d'|'e'|'f'|'g'|'h'|'i'|'j'|'k'|'l'|'m'|'n'|'o'|'p'|'q'|'r'|'s'|'t'|'u'|'v'|'w'|'x'|'y'|'z'|'A'|'B'|'C'|'D'|'E'|'F'|'G'|'H'|'I'|'J'|'K'|'L'|'M'|'N'|'O'|'P'|'Q'|'R'|'S'|'T'|'U'|'V'|'W'|'X'|'Y'|'Z'
digit = '0'|'1'|'2'|'3'|'4'|'5'|'6'|'7'|'8'|'9'
hspaces = (' ' | '\t' | escaped_linebreak)*
hspacesp = (' ' | '\t' | escaped_linebreak)+
escaped_linebreak = '\\' {'\n'}
space = '\t'|'\n'|'\r'|' '|comment
spaces = space*
"""

tree = ['And',
 ['rule', ['rule_name', 'name'], ['flags'], ['args'],
  ['and',
   ['or', ['apply', 'letter'], ['exactly', '_']],
   ['quantified',
    ['or', ['apply', 'letter'], ['apply', 'digit'], ['exactly', '_']],
    ['quantifier', '*']]]],
 ['rule', ['rule_name', 'expr'], ['flags'], ['args'],
  ['or',
   ['apply', 'apply'], ['apply', 'exactly'], ['apply', 'token'],
   ['apply', 'parenthesis'], ['apply', 'output']]],
 ['rule', ['rule_name', 'exactly'], ['flags', '!'], ['args'],
  ['and',
   ['token', "'"],
   ['output',
    ['quantified',
     ['or', ['apply', 'escaped_char'],
            ['and', ['negation', ['exactly', "'"]], ['apply', 'anything']]],
     ['quantifier', '*']]],
   ['token', "'"]]],
 ['rule', ['rule_name', 'token'], ['flags', '!'], ['args'],
  ['and',
   ['token', '"'],
   ['output',
    ['quantified',
     ['or',
      ['apply', 'escaped_char'],
      ['and', ['negation', ['exactly', '"']], ['apply', 'anything']]],
     ['quantifier', '*']]],
   ['token', '"']]],
 ['rule', ['rule_name', 'escaped_char'], ['flags', '!'], ['args'], ['and',
   ['exactly', '\\'],
   ['output', ['or'] + [['exactly', s] for s in 'nrtbf"\'\\']]]],
 ['rule', ['rule_name', 'apply'], ['flags', '!'], ['args'],
  ['and', ['quantified', ['or', ['exactly', '\t'], ['exactly', ' ']],
                         ['quantifier', '*']],
          ['output', ['apply', 'name']]]],
 ['rule', ['rule_name', 'parenthesis'], ['flags'], ['args'],
  ['and', ['token', '('], ['output', ['apply', 'or']], ['token', ')']]],
 ['rule', ['rule_name', 'output'], ['flags', '!'], ['args'],
  ['and', ['token', '{'], ['output', ['apply', 'or']], ['token', '}']]],
 ['rule', ['rule_name', 'not'], ['flags'], ['args'], ['or',
   ['and',
    ['token', '~'],
    ['output', ['bound', ['apply', 'expr'], ['inline', 'negation']]]],
   ['apply', 'expr']]],
 ['rule', ['rule_name', 'quantified'], ['flags'], ['args'],
  ['and',
   ['apply', 'not'],
   ['quantified',
    ['bound',
     ['or', ['exactly', '*'], ['exactly', '+'], ['exactly', '?']],
     ['inline', 'quantifier']],
    ['quantifier', '?']]]],
 ['rule', ['rule_name', 'bound'], ['flags'], ['args'],
  ['and',
   ['apply', 'quantified'],
   ['quantified',
    ['and',
     ['exactly', '='],
     ['output', ['bound', ['apply', 'name'], ['inline', 'inline']]]],
    ['quantifier', '?']]]],
 ['rule', ['rule_name', 'and'], ['flags'], ['args'],
  ['quantified', ['apply', 'bound'], ['quantifier', '*']]],
 ['rule', ['rule_name', 'or'], ['flags'], ['args'], ['and',
   ['apply', 'and'],
   ['quantified',
    ['and', ['token', '|'], ['output', ['apply', 'and']]],
    ['quantifier', '*']]]],
 ['rule', ['rule_name', 'rule'], ['flags'], ['args'],
  ['and',
   ['apply', 'spaces'],
   ['output',
    ['and',
     ['bound', ['apply', 'name'], ['inline', 'rule_name']],
     ['bound',
      ['quantified', ['exactly', '!'], ['quantifier', '?']],
      ['inline', 'flags']],
     ['bound', ['apply', 'and'], ['inline', 'args']],
     ['and', ['token', '='], ['output', ['apply', 'or']]]]]]],
 ['rule', ['rule_name', 'grammar'], ['flags'], ['args'],
  ['and',
   ['output', ['quantified', ['apply', 'rule'], ['quantifier', '*']]],
   ['apply', 'spaces']]],
 ['rule', ['rule_name', 'letter'], ['flags'], ['args'],
  ['or'] + [['exactly', s]
            for s in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ']],
 ['rule', ['rule_name', 'digit'], ['flags'], ['args'],
  ['or'] + [['exactly', s] for s in '0123456789']],
 ['rule', ['rule_name', 'space'], ['flags'], ['args'],
  ['or'] + [['exactly', s] for s in '\t\n\r ']],
 ['rule', ['rule_name', 'spaces'], ['flags'], ['args'],
  ['quantified', ['apply', 'space'], ['quantifier', '*']]]]

if __name__ == "__main__":
    import sys
    i1 = Interpreter(simple_wrap_tree(tree))
    match_tree1 = i1.match(i1.rules['grammar'][-1], grammar + extra)
    i2 = Interpreter(match_tree1)
    match_tree2 = i2.match(i2.rules['grammar'][-1], python_grammar + extra)
    pyi = Interpreter(match_tree2, whitespace="\t \\")
    ast = pyi.match(pyi.rules['file_input'][-1], open(sys.argv[-1]).read())
    ast.pprint()
