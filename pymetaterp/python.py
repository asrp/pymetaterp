import boot_stackless as boot
reload(boot)
from boot_stackless import *
import pdb

class Interpreter(boot.Interpreter):
    def match(self, root, input=None, pos=-1, debug=False):
        self.indentation = [0]
        self.locals = {}
        self.debug = debug
        self.memoizer = {}
        return boot.Interpreter.match(self, root, input, pos)

    def eval(self, root):
        self.locals['self'] = self
        output = eval(root, globals(), self.locals)
        del self.locals['self']
        return output

    def new_step(self):
        root = self.stack[-1].root
        name = root.name
        calls = self.stack[-1].calls
        if name in ["and", "args", "output", "or"]:
            if len(root) == 0 and name in ["and", "args", "output"]:
                return
            calls.extend(root)
        elif name in ["lookahead"]:
            calls.append(root[0])
        elif name == "exactly":
            for char in root[0]:
                if pop(self.input) != char:
                    return MatchError("Not exactly %s" % root[0])
            return root[0]
        elif name == "token":
            while pop(self.input) in ['\t', ' ', '\\']:
                if self.input[0][self.input[1]] == '\\':
                    pop(self.input)
            if self.input[1] == len(self.input[0]):
                return MatchError("EOF")
            self.input[1] -= 1
            for char in root[0]:
                if pop(self.input) != char:
                    return MatchError("Not exactly %s" % root[0])
            if root[0].isalpha():
                top = pop(self.input)
                if top.isalnum() or top == '_':
                    return MatchError("Prefix matched but didn't end.")
                self.input[1] -= 1
            return root[0]
        elif name == "apply":
            if self.debug:
                print " "*len(self.stack), "matching", name, root[NAME], self.input[1], self.input[0][self.input[1]+1:self.input[1]+11]
            if root[NAME] == "anything":
                return pop(self.input)
            elif root[NAME] == "void":
                return
            else:
                key = (root[NAME], id(self.input[0]), self.input[1],
                       tuple(self.indentation))
                if key in self.memoizer:
                    self.input = self.memoizer[key][1][:]
                    return self.memoizer[key][0]
                self.stack[-1].key = key
                calls.append(self.rules[root[NAME]][BODY])
            self.stack[-1].locals = self.locals
            self.locals = {}
        elif name == "rule_value":
            return self.eval(root[0])
        elif name == "predicate":
            output = self.eval(root[0])
            if not output:
                return MatchError("Predicate evaluates to false")
            elif output == True:
                return None
            else:
                return Node("predicate", [output])
        elif name == "action":
            self.locals['self'] = self
            exec(root[0], globals(), self.locals)
            del self.locals['self']
            return
        else:
            return boot.Interpreter.new_step(self)
        return Eval

    def next_step(self):
        frame = self.stack[-1]
        root = frame.root
        name = root.name
        outputs = frame.outputs
        output = outputs[-1] if outputs else None
        is_error = type(output) == MatchError
        finished = len(outputs) == len(frame.calls)
        if is_error and name not in ["quantified", "or", "negation", "apply"]:
            return output
        elif not (finished or name in ["or", "quantified"]):
            return Eval
        if name in ["and", "args", "output"]:
            assert(len(outputs) == len(root))
            if any(child.name == "output" for child in root):
                outputs = [output for child, output in zip(root, outputs)
                           if child.name == "output"]
            elif any(child.name == "rule_value" for child in root):
                outputs = [output for child, output in zip(root, outputs)
                           if child.name == "rule_value"]
                assert(len(outputs) == 1)
            return to_node(outputs, self.join_str)
        elif name in "bound":
            if root[1].name == "inline":
                return Node(root[1][0], to_list(output))
            else: # bind
                self.locals[root[1][0]] = output
                return
        elif name == "apply":
            # Need to run this line even on error
            self.locals = frame.locals
            output = boot.Interpreter.next_step(self)
            self.memoizer[frame.key] = (output, self.input[:])
            return output
        elif name == "lookahead":
            self.input = frame.input[:]
            return output
        else:
            return boot.Interpreter.next_step(self)
        return Eval

def reformat_atom(atom, trailers):
    output = atom
    for trailer in to_list(trailers):
        pos = (output.pos[0], trailer.pos[1])
        if trailer.name == "arglist":
            output = Node("__call__", [output, trailer])
        elif trailer.name == "NAME":
            output = Node("__getattr__", [output, Node("NAME", trailer)])
            output[1].pos = trailer.pos
        elif trailer.name == "subscriptlist":
            output = Node("__getitem__", [output] + trailer)
        else:
            raise Exception("Unknown trailer %s" % trailer.name)
        output.pos = pos
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
            pos = (lhs.pos[0], rhs.pos[1])
            lhs = Node("__binary__", [op, lhs, rhs])
            lhs.pos = pos
        return (lhs, index)
    if not oper_and_atoms:
        return start
    oper_and_atoms = zip(oper_and_atoms[::2], oper_and_atoms[1::2])
    return parse(start, oper_and_atoms)[0]

def any_token(input, binary=True):
    ops = binary_ops if binary else expr_ops
    old_input = input[:]
    for tokens in ops:
        for token in tokens:
            if all(pop(input) == char for char in token):
                return token
            input[:] = old_input[:]
    return False
