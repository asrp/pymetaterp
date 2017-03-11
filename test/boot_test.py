import sys
sys.path.append('.')
sys.setrecursionlimit(5000)
from pymetaterp.util import simple_wrap_tree
from pymetaterp import boot_tree, boot_stackless as boot, boot_grammar

grammar = boot_grammar.bootstrap + boot_grammar.extra
i1 = boot.Interpreter(simple_wrap_tree(boot_tree.tree))
match_tree = i1.match(i1.rules['grammar'][-1], grammar)
i2 = boot.Interpreter(match_tree)
match_tree2 = i2.match(i2.rules['grammar'][-1], grammar)
i3 = boot.Interpreter(match_tree2)
for i in range(3):
    match_tree3 = i3.match(i3.rules['grammar'][-1], grammar)
    i3 = boot.Interpreter(match_tree3)
grammar += boot_grammar.diff
match_tree3 = i3.match(i3.rules['grammar'][-1], grammar)
print match_tree == match_tree2
