from util import MatchError
from pdb import set_trace as bp

inf = float("inf")

class Glob(object):
    pass

g = Glob()

class Source():
    def __init__(self, source):
        self.source = source
        self.position = -1
    def next(self):
        self.position += 1
        try:
            return self.source[self.position]
        except IndexError:
            return MatchError("EOF")

class Node(object):
    def __init__(self, name, children, pos=(None, None)):
        self.name = name
        self.children = children
        self.pos = pos
    def __getitem__(self, index):
        if type(self.children) == list:
            return self.children[index]
        else:
            return [self.children][index]
    def __len__(self):
        return len(self.children) if isinstance(self.children, list) else 1 if self.children else 0
    def __repr__(self):
        return "%s(%s)" % (self.name, self.children)
    def pprint(self, indent=0):
        print " "*indent + self.name
        children = [self.children] if not isinstance(self.children, list) else self.children
        for child in children:
            if not hasattr(child, "pprint"):
                print " "*(indent + 1), type(child).__name__, repr(child)
            else:
                child.pprint(indent + 2)

def to_list(value):
    return value if isinstance(value, list) else\
           [] if value is None else\
           [value]

def exactly(char):
    ichar = g.input.next()
    return ichar if isinstance(ichar, MatchError) or char == ichar\
        else MatchError("Not exactly %s" % char)

def between(start, end):
    ichar = g.input.next()
    return ichar if isinstance(ichar, MatchError) or start <= ichar <= end\
        else MatchError("Not between %s and %s" % (start, end))

def token(s):
    while g.input.next() in ['\t', '\n', '\r', ' ']:
        pass
    g.input.position -= 1
    for char in s:
        if g.input.next() != char:
            return MatchError("Not exactly %s" % char)
    return s

def or_(children):
    saved = g.input.position
    for child in children:
        g.input.position = saved
        output = child()
        if not isinstance(output, MatchError):
            return output
    g.input.position = saved
    return MatchError("No OR child matches")

def and_(children):
    saved = g.input.position
    outputs = []
    output_mode = False
    for child in children:
        output = child()
        if isinstance(output, MatchError):
            g.input.position = saved
            return MatchError("And match failed")
        if output_mode:
            if getattr(output, "name", None) == "out":
                outputs.extend(to_list(output.children))
        else:
            if getattr(output, "name", None) == "out":
                outputs = output.children
                output_mode = True
            else:
                outputs.extend(to_list(output))
    return "".join(outputs) if outputs and type(outputs) == list and all(type(output) == str for output in outputs) and len(outputs[0]) == 1\
        else outputs

def out(child=lambda: None):
    output = child()
    return output if isinstance(output, MatchError) else Node("out", output)

def quantified(child, (_, quantifier)):
    lower, upper = {"*": (0, inf), "+": (1, inf), "?": (0, 1)}[quantifier]
    outputs = []
    count = 0
    start_saved = g.input.position
    while count < upper:
        saved = g.input.position
        output = child()
        if isinstance(output, MatchError):
            if count < lower:
                g.input.position = start_saved
                return MatchError("Quantified undermatch %s < %s" % (count, lower))
            else:
                g.input.position = saved
                return outputs
        outputs.extend(to_list(output))
        count += 1
    return outputs

def negation(child):
    saved = g.input.position
    output = child()
    g.input.position = saved
    return None if isinstance(output, MatchError) else MatchError("Negation_is_true")

def bound(child, (_, name)):
    saved = g.input.position
    output = child()
    return output if isinstance(output, MatchError) else\
        Node(name, output, (saved+1, g.input.position+1))

def apply_(name):
    saved = g.input.position
    # func, flagged
    output = g.rules[name][0]()
    if isinstance(output, MatchError):
        return output
    if name == "escaped_char":
        return({"t": "\t", "n": "\n", "\\\\": "\\", "r": "\r"}.get(output, output))
    if name == "balanced":
        return output
    if "!" in g.rules[name][1] or (isinstance(output, list) and len(output) > 1):
        return Node(name, output, (saved+1, g.input.position+1))
    return output

def rule_anything():
    char = g.input.next()
    return MatchError("End_of_file") if char is None else char

def rule_letter():
    return(or_([lambda: between("a", "z"), lambda: between("A", "Z")]))

def rule_digit():
    return(between("0", "9"))

def closure(child, value):
    return str(value) if isinstance(child, str) or child.name in ["quantifier", "inline", "bind"] else "lambda: %s" % value

def to_python(root):
    if isinstance(root, str):
        return repr(root)
    elif type(root) == list:
        #names = [rule[0][0] for rule in root] + ["letter", "digit", "anything"]
        named = ", ".join(['"%s": (rule_%s, %s)' % (rule[0][0], rule[0][0], repr("".join(rule[1])))
                           for rule in root])
        return "\n\n".join(to_python(child) for child in root
                           if child[0][0] not in ["letter", "digit"]) +\
               "\n\ng.rules.update({%s})" % named
    name = root.name + "_" if root.name in ["and", "or", "apply"] else root.name
    if name in ["quantifier", "inline", "bind"]:
        return (name, to_python(root[0])[1:-1])
    elif name == "rule":
        return "def rule_%s():\n    return %s" % (root[0][0], to_python(root[-1]))
    else:
        children = ", ".join(closure(child, to_python(child))
                             for child in root)
        if name in ["and_", "or_"]:
            children = "[%s]" % children
        if name == "output":
            name = "out"
        return "%s(%s)" % (name, children)

def gen_from_tree():
    import boot_tree
    from util import simple_wrap_tree
    return to_python(list(simple_wrap_tree(boot_tree.tree)))

def match(tree, inp):
    g.rules = {'anything': (rule_anything, ''), 'letter': (rule_letter, ''),
               'digit': (rule_digit, '')}
    exec to_python(tree)
    g.input = Source(inp)
    return rule_grammar()

if __name__ == "__main__":
    from boot_grammar import bootstrap
    exec gen_from_tree()
    #g.input = Source("foo = bar")
    g.input = Source(bootstrap)
    output = rule_grammar()
    print to_python(output)
    exec to_python(output)
    g.input = Source(bootstrap)
    output2 = rule_grammar()
    assert(to_python(output) == to_python(output2))
