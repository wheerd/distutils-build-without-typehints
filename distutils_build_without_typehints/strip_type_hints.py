# -*- coding: utf-8 -*-
import ast
import itertools
import operator
from lib2to3.fixer_base import BaseFix
from lib2to3.fixer_util import Call as TCA
from lib2to3.fixer_util import Comma, Dot, Name, Newline, is_probably_builtin
from lib2to3.patcomp import PatternCompiler
from lib2to3.pgen2 import token
from lib2to3.pygram import python_symbols as syms
from lib2to3.pytree import Leaf, Node
from lib2to3.refactor import FixerError, RefactoringTool

def node_post_order(self):
    """Return a post-order iterator for the tree."""
    for child in self.children[:]:
        yield from child.post_order()
    yield self

def node_pre_order(self):
    """Return a pre-order iterator for the tree."""
    yield self
    for child in self.children[:]:
        yield from child.pre_order()


# We replace the Node's post_order() and pre_order() methods here
# The only change is that they use a copy of the children so that we can remove children while iterating without
# causing an issue
Node.pre_order = node_pre_order
Node.post_order = node_post_order

def replace_cast(node):
    i = 1
    while node.children[i].type == syms.trailer and node.children[i].children[0].type == token.DOT:
        i += 1
    call = node.children[i]
    if call.type != syms.trailer or len(call.children) != 3 or call.children[0].type != token.LPAR:
        return

    expression = call.children[1].children[2]

    node.replace(expression)

def remove_expr(node):
    if node.parent.type == syms.arglist:
        potential_comma = node.prev_sibling
        if potential_comma is not None and potential_comma.type == token.COMMA:
            potential_comma.remove()
        node.remove()
    elif node.parent.type == syms.expr_stmt:
        node.parent.parent.remove()
    else:
        node.remove()

def remove_line(node):
    while node.type != syms.simple_stmt:
        node = node.parent
    node.remove()

def with_seperator(items, seperator):
    if len(items) == 0:
        return []
    result = []
    for item in items[:-1]:
        result.append(item)
        result.append(seperator())
    result.append(items[-1])
    return result

def DottedName(name, prefix=None):
    if '.' in name:
        parts = [Name(n) for n in name.split('.')]
        return Node(syms.dotted_name, with_seperator(parts, Dot), prefix=prefix)

    return Name(name, prefix)


def FromImport(package_name, names):
    dotted_name = DottedName(package_name)
    dotted_name.prefix = ' '

    leafs = []
    for name, alias in names:
        if alias is None or alias == name:
            leafs.append(Name(name, prefix=' '))
        else:
            leafs.append(Node(syms.import_as_name, [Name(name, prefix=' '), Name('as', prefix=' '), Name(alias, prefix=' ')]))

    children = [Leaf(token.NAME, "from"),
                dotted_name,
                Leaf(token.NAME, "import", prefix=" "),
                Node(syms.import_as_names, with_seperator(leafs, Comma))]
    imp = Node(syms.import_from, children)
    return imp

class FixRemoveCast(BaseFix):

    IMPORT_PATTERN = PatternCompiler().compile_pattern("""
        import_name< 'import' modulename='typing' >
        |
        import_name< 'import' dotted_as_name< 'typing' 'as'
           modulename=any > >
        |
        import_from< 'from' 'typing' 'import' ['('] imports=import_as_names< any* > [')'] >
        |
        import_from< 'from' 'typing' 'import' ['('] imports=import_as_name< any* > [')'] >
        """)

    TYPES = {
        'AbstractSet': 'collections.abc.Set',
        'Any': 'object',
        'AsyncIterable': 'collections.abc.AsyncIterable',
        'AsyncIterator': 'collections.abc.AsyncIterator',
        'Awaitable': 'collections.abc.Awaitable',
        'ByteString': 'str',
        'Callable': remove_expr,
        'cast': replace_cast,
        'ClassVar': remove_expr,
        'Collection': 'collections.abc.Collection',
        'Container': 'collections.abc.Container',
        'Coroutine': 'collections.abc.Coroutine',
        'DefaultDict': 'collections.defaultdict',
        'Dict': 'dict',
        'FrozenSet': 'frozenset',
        'Generator': 'types.GeneratorType',
        'Generic': remove_expr,
        'Hashable': 'collections.abc.Hashable',
        'ItemsView': 'collections.abc.ItemsView',
        'Iterable': 'collections.abc.Iterable',
        'Iterator': 'collections.abc.Iterator',
        'KeysView': 'collections.abc.KeysView',
        'List': 'list',
        'Mapping': 'collections.abc.Mapping',
        'MappingView': 'collections.abc.MappingView',
        'MutableMapping': 'collections.abc.MutableMapping',
        'MutableSequence': 'collections.abc.MutableSequence',
        'MutableSet': 'collections.abc.MutableSet',
        'NamedTuple': 'collections.namedtuple',
        'NewType': remove_line,
        'Optional': remove_expr,
        'overload': remove_expr,
        'Reversible': 'collections.abc.Reversible',
        'Sequence': 'collections.abc.Sequence',
        'Set': 'set',
        'Sized': 'collections.abc.Sized',
        'Tuple': 'tuple',
        'Type': 'type',
        'TypeVar': remove_line,
        'Union': remove_expr,
        'ValuesView': 'collections.abc.ValuesView',
    }

    def start_tree(self, tree, filename):
        super(FixRemoveCast, self).start_tree(tree, filename)
        # Reset the patterns attribute for every file:
        self.usage_patterns = []
        self.aliases = {}
        self.patterns = set()
        self.imports = set()

    def match(self, node):
        # Match the import patterns:
        results = {"node": node}
        match = self.IMPORT_PATTERN.match(node, results)

        if match and 'imports' in results:
            imports = results['imports']

            replace_imports = {}

            if imports.type == token.STAR:
                for type, replacement in self.TYPES.items():
                    self.make_pattern(type)
                    if isinstance(replacement, str) and '.' in replacement:
                        module, name = replacement.rsplit('.', 1)
                        replace_imports.setdefault(module, set()).add((name, type))
            elif imports.type == self.syms.import_as_names:
                for child in imports.children:
                    if child.type == token.NAME:
                        self.make_pattern(child.value)
                        replacement = self.TYPES.get(child.value)
                        if isinstance(replacement, str) and '.' in replacement:
                            module, name = replacement.rsplit('.', 1)
                            replace_imports.setdefault(module, set()).add((name, child.value))
                    elif child.type == self.syms.import_as_name:
                        name = child.children[0].value
                        alias = child.children[2].value if len(child.children) > 1 else None
                        self.make_pattern(name, alias=alias)
                        replacement = self.TYPES.get(name)
                        if isinstance(replacement, str) and '.' in replacement:
                            module, import_name = replacement.rsplit('.', 1)
                            replace_imports.setdefault(module, set()).add((import_name, alias))
                    else:
                        continue
            elif imports.type == self.syms.import_as_name:
                name = imports.children[0].value
                alias = imports.children[2].value if len(imports.children) > 1 else None
                self.make_pattern(name, alias=alias)
                replacement = self.TYPES.get(name)
                if isinstance(replacement, str) and '.' in replacement:
                    module, import_name = replacement.rsplit('.', 1)
                    replace_imports.setdefault(module, set()).add((import_name, alias))

            results['replace_imports'] = replace_imports

            return results

        if match and 'modulename' in results:
            modname = results['modulename'].value

            replace_imports = set()
            for type, replacement in self.TYPES.items():
                self.make_pattern(type, modname=modname)
                if isinstance(replacement, str) and '.' in replacement:
                    module, _ = replacement.rsplit('.', 1)
                    replace_imports.add(module)

            results['replace_imports'] = replace_imports
            return results

        # Now do the usage patterns
        for pattern in self.usage_patterns:
            if pattern.match(node, results):
                return results

    def make_pattern(self, name, modname=None, alias=None):
        attribute_name = 'name' if alias is None else 'alias'
        if (name, modname, alias) in self.patterns:
            return
        if alias is not None:
            self.aliases[alias] = name
            name = alias
        simple_patterns = ["power< %s='%s' any* >"]
        patterns = ["power< '%s' trailer< '.' %s='%s' > any* >"]
        if name == 'overload':
            simple_patterns = [
                "decorated< decorators< any* decorator< '@' %s='%s' any* > any* > any* >",
                "decorated< decorator< '@' %s='%s' any* > any* >"
            ]
            patterns = [
                "decorated< decorators< any* decorator< '@' dotted_name< '%s' '.' %s='%s' > any* > any* > any* >",
                "decorated< decorator< '@' dotted_name< '%s' '.' %s='%s' > any* > any* >"
            ]

        if modname is not None:
            for pattern in patterns:
                self.usage_patterns.append(PatternCompiler().compile_pattern(
                    pattern % (modname, attribute_name, name)))
        else:
            for pattern in simple_patterns:
                patt_str = pattern % (attribute_name, name)
                #print(patt_str)
                self.usage_patterns.append(PatternCompiler().compile_pattern(
                    patt_str))

        self.patterns.add((name, modname, alias))

    def transform(self, node, results):
        if node.type in (self.syms.import_from, self.syms.import_name):
            if 'replace_imports' in results and results['replace_imports']:
                imports = results['replace_imports']

                if isinstance(imports, set):
                    imps = [Node(syms.import_name, [Name('import'), DottedName(n, prefix=' ')]) for n in imports if not n in self.imports]
                    self.imports.update(imports)
                    replacement = with_seperator(imps, Newline)

                else:
                    replacement = with_seperator([FromImport(p, n) for p, n in imports.items()], Newline)

                node.replace(replacement)
            else:
                prev = node.prev_sibling
                if prev is not None and prev.type == token.SEMI:
                    prev.remove()
                parent = node.parent
                node.remove()
                if len(parent.children) == 1 and parent.children[0].type == token.NEWLINE:
                    parent.remove()

        if 'name' in results or 'alias' in results:
            if 'name' in results:
                name = results['name'].value
            else:
                name = self.aliases[results['alias'].value]

            if name in self.TYPES:
                replacement = self.TYPES[name]
                if callable(replacement):
                    replacement(node)
                elif isinstance(replacement, str):
                    if '.' in replacement:
                        i = 1
                        while node.children[i].type == syms.trailer and node.children[i].children[0].type == token.DOT:
                            i += 1
                        if i > 1:
                            node.replace(DottedName(replacement))
                        else:
                            square = node.children[i]
                            if square.type == syms.trailer and len(square.children) == 3 and square.children[0].type == token.LSQB:
                                square.remove()
                    else:
                        node.replace(Name(replacement))

            #node.replace(results['expr'])

class FixRemoveGenericBases(BaseFix):

    PATTERN = """
        classdef< 'class' name=any '(' args=arglist< any* power< any generic=trailer< '[' any* ']' > > any* > ')' ':' any >
        |
        classdef< 'class' name=any '(' args=power< any generic=trailer< '[' any* ']' > > ')' ':' any >
        """

    run_order = 10

    def transform(self, node, results):
        results['generic'].remove()

class FixRemoveTypeHints(BaseFix):

    PATTERN = """
        tname< name=any ':' [any] >
        |
        funcdef< 'def' any any '->' hint=any ':' any >
        """

    run_order = 4

    def transform(self, node, results):
        if 'name' in results:
            node.replace(results['name'])
        else:
            arrow = results['hint'].prev_sibling
            results['hint'].remove()
            arrow.remove()
            node.changed()

class StripTypeHintsRefactoringTool(RefactoringTool):
    def __init__(self):
        super().__init__([FixRemoveCast, FixRemoveTypeHints, FixRemoveGenericBases], {})

    def get_fixers(self):
        pre_order_fixers = []
        post_order_fixers = []
        for fix_class in self.fixers:
            fixer = fix_class(self.options, self.fixer_log)

            self.log_debug("Adding transformation: %s", fix_class.__name__)
            if fixer.order == "pre":
                pre_order_fixers.append(fixer)
            elif fixer.order == "post":
                post_order_fixers.append(fixer)
            else:
                raise FixerError("Illegal fixer order: %r" % fixer.order)

        key_func = operator.attrgetter("run_order")
        pre_order_fixers.sort(key=key_func)
        post_order_fixers.sort(key=key_func)
        return (pre_order_fixers, post_order_fixers)
