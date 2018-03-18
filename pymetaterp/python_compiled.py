from boot_compiled import *

def eval_(expr):
    g.locals['self'] = g
    output = eval(expr, globals(), g.locals)
    del g.locals['self']
    return output

def lookahead(child):
    saved = g.input.position
    output = child()
    g.input.position = saved
    return output

def token(s):
    while g.input.next() in ['\t', '\n', '\r', ' ']:
        pass
    g.input.position -= 1
    for char in s:
        if g.input.next() != char:
            return MatchError("Not exactly %s" % char)
    if char.isalpha():
        top = g.input.next()
        if top.isalnum() or top == '_':
            return MatchError("Prefix matched but didn't end.")
        g.input.position -= 1
    return s

def and_(children):
    saved = g.input.position
    outputs = []
    output_mode = None
    for child in children:
        output = child()
        if isinstance(output, MatchError):
            g.input.position = saved
            return MatchError("And match failed")
        if output_mode:
            if getattr(output, "name", None) == output_mode:
                outputs.extend(to_list(output.children))
        else:
            if getattr(output, "name", None) == "out":
                outputs = to_list(output.children)
                output_mode = "out"
            elif getattr(output, "name", None) == "rule_value":
                outputs = to_list(output.children)
                output_mode = "rule_value"
            else:
                outputs.extend(to_list(output))
    return "".join(outputs) if outputs and all(type(output) == str for output in outputs) and len(outputs[0]) == 1\
        else outputs

# Not a rule! Should rename this node to just 'value'?
def rule_value(expr):
    # Not normally wrapped in Node, need to rethink!
    return Node("rule_value", eval_(expr))

def predicate(expr):
    output = eval_(expr)
    if not output:
        return MatchError("Predicate evaluates to false")
    elif output == True:
        return None
    else:
        return Node("predicate", [output])

def action(expr):
    g.locals['self'] = g
    exec(expr, globals(), g.locals)
    del g.locals['self']
    return

def bound(child, (type, name)):
    saved = g.input.position
    output = child()
    if type == "inline":
        return output if isinstance(output, MatchError) else\
            Node(name, output, (saved+1, g.input.position+1))
    else: # bind
        g.locals[name] = output

def apply_(name):
    if g.debug:
        print " "*g.nest, name, g.input.source[g.input.position+1: g.input.position+10]
    key = (name, id(g.input.source), g.input.position, tuple(g.indentation))
    # Should also memoize output indentation!
    if key in g.memoizer:
        g.input.source, g.input.position = g.memoizer[key][1][:]
        return g.memoizer[key][0]
    saved_locals = g.locals
    g.locals = g.default_locals
    # func, flagged
    g.nest += 1
    saved = g.input.position
    output = g.rules[name][0]()
    g.nest -= 1
    if g.debug:
        print " "*g.nest, name, "->", output
    g.locals = saved_locals
    if (not isinstance(output, MatchError) and "!" in g.rules[name][1]) or\
       (isinstance(output, list) and len(output) > 1):
        output = Node(name, output, (saved+1, g.input.position+1))
    g.memoizer[key] = (output, [g.input.source, g.input.position])
    return output

def rule_void():
    return

def reformat_atom(atom, trailers):
    if trailers:
        bp()
    output = atom
    for trailer in trailers:
        pos = (output.pos[0], trailer.pos[1])
        if trailer.name == "arglist":
            output = Node("__call__", [output, trailer], pos=pos)
        elif trailer.name == "NAME":
            output = Node("__getattr__", [output, Node("NAME", trailer,
                                                       pos=trailer.pos)], pos=pos)
        elif trailer.name == "subscriptlist":
            output = Node("__getitem__", [output] + trailer, pos=pos)
        else:
            raise Exception("Unknown trailer %s" % trailer.name)
    return output


binary_ops = ((">=", "<=", "<>", "<", ">", "==", "!=",
               "in", "not in", "is not", "is"),
              ("|",), ("^",), ("&",), ("<<", ">>"), ("+", "-"),
              ("*", "/", "%", "//"), ("**",))
priority = {op:i for i, ops in enumerate(binary_ops) for op in ops}
expr_ops = binary_ops[1:]

def reformat_binary(start, oper_and_atoms):
    def parse(lhs, tokens, index=0):
        threshold = priority[tokens[index][0][0]]
        while index < len(tokens):
            op, rhs = tokens[index]
            assert(type(op) != str)
            op = op[0]
            if priority[op] < threshold:
                break
            index += 1
            while index < len(tokens) and\
                  priority[tokens[index][0][0]] > priority[op]:
                rhs, index = parse(rhs, tokens, index)
            lhs = Node("__binary__", [op, lhs, rhs], pos=(lhs.pos[0], rhs.pos[1]))
        return (lhs, index)
    if not oper_and_atoms:
        return start
    tokens = zip(oper_and_atoms[::2], oper_and_atoms[1::2])
    lhs, index = start[0], 0
    while index < len(tokens):
        lhs, index = parse(lhs, tokens, index)
    return lhs

def any_token(input, binary=True):
    ops = binary_ops if binary else expr_ops
    old_input = g.input.position
    for tokens in ops:
        for token in tokens:
            if all(g.input.next() == char for char in token):
                return token
            g.input.position = old_input
    return False

def match(tree, inp, debug=False, locals=None):
    g.rules = {'anything': (rule_anything, ''), 'letter': (rule_letter, ''),
               'digit': (rule_digit, ''), 'void': (rule_void, ''),}
    g.indentation = [0]
    g.memoizer = {}
    g.locals = g.default_locals = {} if locals is None else dict(locals)
    g.nest = 0
    g.debug = debug
    exec to_python(tree)
    g.input = Source(inp)
    return rule_grammar()
