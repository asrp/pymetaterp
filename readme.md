# pymetaterp

This is a python AST builder that uses no Python modules. A longer stackless version is available for easier porting. `single_file.py` is a stand-alone 502 lines script.

Its (also) just another parsing expression grammar (PEG) based parser with one major difference. The parsed grammar is interpreted instead of compiled. This makes it easy to modify the language (by editing its grammar) *as well as* the language that grammar is written in (and the language of *that* grammar).

[This is a **pre-release** of sorts. There are probably some errors and missing information.]

## Download and run

    git clone https://github.com/asrp/pymetaterp
    cd pymetaterp
    python single_file.py

or

    python single_file.py filename.py

This will print out the AST of the given file (or `single_file.py`'s own AST). Sample beginning of the output:

    file_input
      regular_assign
        testlist
          NAME
            str 'NAME'
          NAME
            str 'FLAGS'

To run files from the library

    python test/boot_test.py 
    python test/python_parse_test.py 

## Files

`single_file.py` is mainly for demonstration. This module is otherwise separated into files. There are many files but they are mostly separate. The import dependencies is

    util.py
      boot.py
      boot_stackless.py
        python.py

Other files have no imports. To get something useful, you'll have to import multiple files. See `test/python_parse_test.py` and `test/boot_test.py` for some examples.

## Repl

An obvious thing *missing* is the grammar read-eval-print loop (repl) so the interpreter can be fed one rule at a time, parsing subsequence input using the rules seen so far.

## Source reading order

I'd suggest reading `boot.py` and `bootstrap` in `boot_grammar.py` first. The two form the core and together with `boot_tree.py`, they can regenerate `boot_tree`.

Then `boot_stackless` is the same as `boot.py` but doesn't use the Python call stack/recursion for parsing.

`python.py` adds functionality to the `boot.py` interpreter. `diff` in `boot_grammar.py` adds the syntax for those.

Finally, `python_grammar.py` contains the python grammar to be finally parsed.

## Python language parsed

The module builds the AST for Python 2.x programs. It is able to parse all of Python 2.x (in fact, it contains a slightly modified version of the Python 2.x grammar) but is less lenient with whitespaces. For example, parsing

    from my_module import (var1, var2,
                           var3, var4)

gives an error.

*Since this is a pre-release, there are likely bugs with parts of the language I don't use so often. It _can_ build the AST for all files included here.* 

## Gramamr language differences

The beginning of `boot_grammar.py` self-describes the grammar. Its a PEG so all "or" (`|`) returns the first match and "and" and "quantified" (`*, +, ?`) are greedy.

    name = (letter | '_') (letter | digit | '_')*
    expr = apply | exactly | token | parenthesis | output

    exactly! = "'" {(escaped_char | ~'\'' anything)*} "'"
    token! = "\"" {(escaped_char | ~'"' anything)*} "\""
    escaped_char! = '\\' {'n'|'r'|'t'|'b'|'f'|'"'|'\''|'\\'}
    apply! = ('\t'|' ')* {name}
    parenthesis = "(" {or} ")"
    output! = "{" {or} "}"

    not = "~" {expr=negation} | expr
    quantified = not (('*' | '+' | '?')=quantifier)?
    bound = quantified ('=' {name=inline})?
    and = bound*
    or = and ("|" {and})*

    rule = spaces {name=rule_name '!'?=flags and=args ("=" {or})}
    grammar = {rule*} spaces

The main difference from other PEG.

- output rule: `a {b c} d` will match the concatenation of `a b c d` but only return what matched `b c`.
- quantifier collapse: `letter letter*` returns a list rather than a pair with the second element being a list matching `letter*`.
- nested and collapse: `a (b (c d)) e` has the same output as `a b c d e` (see inline below if some pairs need to be explicitly grouped).
- node collapsing: nodes in the output with only one child are replaced by their parent, unless the `!` ("don't collapse") flag is set for that node.
- inline: shamelessly taken [Ohm](https://github.com/ohm) but with a slightly different interpretation. `expression=name` creates a node named `name` wrapping the output of `expression`.
- rule replacement: having a second `rule_name = expression` line replaces the first definition of `rule_name` (instead of appending into an or).
- two basic tokens: there are two basic token types: `'a'` (single quote) and `"a"` (double quote). The double quoted token allows whitespace before matching.

## Regenerating boot_tree.py

Create some tree `match_tree` using `Interpreter.match` and call `save` on the result.

    match_tree.save("tree.py")

## Left recursion

While "[PEG/packrat parsers can support left-recursion]((http://www.vpri.org/pdf/tr2007002_packrat.pdf))", the tree output isn't the one we want. The python functions `reformat_binary` and `reformat_atom` fixes a parsed tree's ouput.

## Source oddities

### Two hard-coded rules

            if root[NAME] == "anything":
                return pop(self.input)
            elif root[NAME] == "void":
                return

### Hard-coded semantics for tokens

            if name == "token":
                while pop(self.input) in self.whitespace:
                    if self.input[0][self.input[1]] == '\\':
                        pop(self.input)
                self.input[1] -= 1
            if name == "token" and root[0].isalpha():
                top = pop(self.input)
                if top.isalnum() or top == '_':
                    raise MatchError("Prefix matched but didn't end.")
                self.input[1] -= 1

## Optimization

Some effort were made to make these files short (especially `single_file.py`) but not too much. There are still some asserts around and commented print statements that can be useful for debugging. The final goal is, of course, to reduce the program's complexity and verbosity, not its line count.

## Missing features

Features/bloat from a longer version of this program not (yet?) moved over:

- Debugging tree of nodes visited and their input and output
- Function arguments (its in the grammar but not the interpreter)
- Nested list inputs (its also in the grammar but not the interpreter)
- name, args, flags, body as parameters instead of positional children
- ~~Memoization~~
- ~~Matched input start and end positions~~
- Exact python expression matching for predicate, action and rule value. `balanced` is used as a simpler heuristic for now.

## Removing features

To get a smaller file with just the basics.

    patch -R pymetaterp/python.py < patches/python_pos.patch
    patch -R pymetaterp/python.py < patches/python_memoizer.patch
    patch -R pymetaterp/boot_stackless.py < patches/boot_pos.patch
    patch -R pymetaterp/boot_stackless.py < patches/boot_memoizer.patch

## Readings

- [Ometa](http://www.tinlizzie.org/ometa/) - Warth's thesis reads very well.
- [PEG and packrat parser](http://bford.info/packrat/)
- [Packrat Parsers Can Support Left Recursion](http://www.vpri.org/pdf/tr2007002_packrat.pdf)

## Other similar projects

- [parsimonious](https://github.com/erikrose/parsimonious)
- [Pymeta](https://pypi.python.org/pypi/PyMeta/)
- [pyparsing](http://pyparsing.wikispaces.com/)
