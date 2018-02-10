import sys
sys.path.append('.')
sys.setrecursionlimit(5000)
from pymetaterp.util import simple_wrap_tree
from pymetaterp import boot_tree, boot_grammar
from pymetaterp.boot_compiled import to_python, match

t1 = list(simple_wrap_tree(boot_tree.tree))
grammar = boot_grammar.bootstrap + boot_grammar.extra
t2 = match(t1, grammar)
t3 = match(t2, grammar)
assert(to_python(t2) == to_python(t3))
