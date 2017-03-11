import sys
sys.path.append('.')
sys.setrecursionlimit(5000)
from pymetaterp.util import simple_wrap_tree
from pymetaterp import boot_grammar, boot_tree, boot_stackless as boot_terp, python, python_grammar

grammar = boot_grammar.bootstrap + boot_grammar.extra
i1 = boot_terp.Interpreter(simple_wrap_tree(boot_tree.tree))
# Not needed, just double checking
match_tree = i1.match(i1.rules['grammar'][-1], grammar)
i2 = boot_terp.Interpreter(match_tree)
match_tree2 = i2.match(i2.rules['grammar'][-1], grammar + boot_grammar.diff)
i3 = boot_terp.Interpreter(match_tree2)
match_tree3 = i3.match(i3.rules['grammar'][-1], python_grammar.full_definition + python_grammar.extra)
pyi = python.Interpreter(match_tree3)
pyimatch_tree = pyi.match(pyi.rules['grammar'][-1], open("test/python_parse_test.py").read())
pyimatch_tree.pprint()
print len(pyi.input[0]) == pyi.input[1] + 1
