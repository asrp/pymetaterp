def simple_wrap_tree(root):
    if type(root) != list:
        return root
    return Node(root[0], map(simple_wrap_tree, root[1:]))

class MatchError(Exception):
    pass

class Node(list):
    def __init__(self, name=None, value=None, params=None, **kw):
        list.__init__(self, value if value is not None else [])
        self.name = name
        self.params = params if params is not None else {}
        for key, value in kw.items():
            setattr(self, key, value)

    def __repr__(self):
        return "%s%s" % (self.name, list.__repr__(self))

    def pprint(self, max_depth=None, max_width=None, indent=0, filter=None):
        if max_depth and indent/2 > max_depth:
            return
        print_node = bool(filter is None or filter(self))
        if print_node:
            print " "*indent + self.name
        for child in self:
            if not hasattr(child, "pprint"):
                if print_node:
                    print "%s%s %s" % (" "*(indent + 2), type(child).__name__,
                                       repr(child))
            else:
                child.pprint(max_depth, max_width, indent + 2*print_node, filter)

    def save(self, filename="tree.py"):
        from pprint import pprint
        f = open(filename, "w")
        f.write("tree = ")
        pprint(self.to_list(), f)

    def to_list(self):
        return [self.name] + [elem.to_list() if hasattr(elem, "name") else elem

                              for elem in self]

    def to_lisp(self):
        return "(%s)" % " ".join([self.name] +\
                                 [elem.to_lisp() if hasattr(elem, "name") else\
                                  repr(elem).replace("'", '"') if elem != '"' else '"\\""'
                                  for elem in self])

    @property
    def descendants(self):
        for child in self:
            if type(child) == Node:
                for gc in child.descendants:
                    yield gc
            yield child

def compare_trees(t1, t2, indices):
    for ind in indices:
        t1 = t1[ind]
        t2 = t2[ind]
    return [equal_trees(x, y) for x,y in zip(t1, t2)]

def equal_trees(t1, t2):
    if type(t1) != Node or type(t2) != Node:
        return t1 == t2
    return type(t1) == type(t2) and t1.name == t2.name and\
        all(equal_trees(c1, c2) for c1, c2 in zip(t1, t2) if type(t1) == Node)
