import sys
sys.path.append('.')
sys.setrecursionlimit(5000)
from pymetaterp.util import simple_wrap_tree
from pymetaterp import boot_tree, boot_grammar
from pymetaterp.boot_compiled import to_python, match
from pymetaterp import python_compiled, python_grammar

grammar = boot_grammar.bootstrap + boot_grammar.extra
t1 = list(simple_wrap_tree(boot_tree.tree))
t2 = match(t1, grammar)
t3 = match(t2, grammar + boot_grammar.diff)
pytree = match(t3, python_grammar.full_definition + python_grammar.extra)
srctree = python_compiled.match(pytree, open("python_ex.py").read())
srctree.pprint()
