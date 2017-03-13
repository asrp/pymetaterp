from util import MatchError, Node

NAME, FLAGS, ARGS, BODY = [0, 1, 2, 3]
inf = float("inf")
# input is a pair (container, pos)

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

class Interpreter:
    def __init__(self, grammar_tree):
        self.rules = {rule[NAME][0]:rule for rule in grammar_tree}
        self.join_str = True

    def match(self, root, new_input=None, new_pos=-1):
        """ >>> g.match(g.rules['grammar'][-1], "x='y'") """
        if new_input is not None:
            self.input = [new_input, new_pos]
        old_input = self.input[:]
        name = root.name
        #print("matching %s" % name)
        if name in ["and", "args", "body", "output"]:
            outputs = [self.match(child) for child in root]
            if any(child.name == "output" for child in root):
                outputs = [output for child, output in zip(root, outputs)
                           if child.name == "output"]
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
                if last_input == self.input:
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
                while pop(self.input) in ['\t', '\n', '\r', ' ']:
                    pass
                self.input[1] -= 1
            if pop(self.input) == root[0]:
                return root[0]
            else:
                raise MatchError("Not exactly %s" % root)
        elif name == "apply":
            #print "rule %s" % root[NAME]
            if root[NAME] == "anything":
                return pop(self.input)
            outputs = self.match(self.rules[root[NAME]][BODY])
            if root[NAME] == "escaped_char":
                chars = dict(["''", '""', "t\t", "n\n", "r\r",
                              "b\b", "f\f", "\\\\"])
                return chars[outputs]
            and_node = getattr(outputs, "name", None) == "And"
            make_node = "!" in self.rules[root[NAME]][FLAGS] or\
                        (and_node and len(outputs) > 1)
            if not make_node:
                return outputs
            return Node(root[NAME], to_list(outputs))
        elif name in "bound":
            return Node(root[1][0], to_list(self.match(root[0])))
        elif name == "negation":
            try:
                self.match(root[0])
            except MatchError:
                self.input = old_input
                return None
            raise MatchError("Negation true")
        else:
            raise Exception("Unknown operator %s" % name)

        outputs = [elem for output in outputs
                   for elem in to_list(output)]
        if len(outputs) == 1:
            return outputs[0]
        elif len(outputs) == 0:
            return None
        else:
            if self.join_str and all(type(output) == str for output in outputs):
                return "".join(outputs)
            return Node("And", outputs)
