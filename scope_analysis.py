from tokens import Token, tokenize
from parse import BinaryOp, UnaryOp, pprint_tree, parse, Assignment, If, While, Call, Return, Function, Run, PropAccess, Class, Compile, parse_expression

class ScopeAnalyzer:
    def __init__(self):
        self.tables = {}
        self.global_symbol_table = SymbolTable()
        self.done = False

    def __getitem__(self, node):
        # nodes are namedtuples so identical ones compare equal
        # so let's hash by id to use object identity instead.
        if id(node) not in self.tables:
            if self.done:
                raise KeyError(f"No scope found for this ast node: {node}")
            self.tables[id(node)] = SymbolTable()
        return self.tables[id(node)]

    def discover_symbols(self, stmts):
        """Call on a module-level series of statements to determine all scopes"""

        if not isinstance(stmts, list):
            raise ValueError(f"discover_symbols() want a list of statements, not {stmts}")

        # find all assignments - these are global variables
        for stmt in stmts:
            for assign in find_all_assignments(stmt):
                if isinstance(assign.lhs, Token) and assign.lhs.kind == 'Variable':
                    self.global_symbol_table.global_vars.add(assign.lhs.content)

        # find all variables - these are global variables
        for stmt in stmts:
            for lookup in find_all_variable_lookups(stmt):
                name = lookup.content
                self.global_symbol_table.global_vars.add(name)

        for stmt in stmts:
            for nested_scope in find_all_nested_scopes(stmt):
                # nested scopes at this level need no information
                # about the global scope: variables are assumed global
                # if when not found regardless of declared global variables
                determine_scopes(nested_scope, {}, self.global_symbol_table, self)

        self.done = True

class SymbolTable:
    def __init__(self):
        self.local_vars = set()  # may not include params, so parms need to be added
        self.global_vars = set()
        self.free_vars = {}  # mapping to owning symbol table
        self.cell_vars = set()  # known to be used by others
        self.parent = None

    def set_parent(self, parent):
        assert self.parent is None
        self.parent = parent

    def mark_as_cell_var(self, name):
        assert name in self.cell_vars or name in self.local_vars, f"name {name} not in cell_vars or locals of {self}"
        if name in self.local_vars:
            self.local_vars.remove(name)
        self.cell_vars.add(name)

    def mark_or_add_as_free_var(self, name, originating_symbol_table):
        if name in self.local_vars:
            #TODO could this ever happen?
            self.local_vars.remove(name)
        if name in self.free_vars:
            # symbol table might already use this name as free_var
            assert self.free_vars[name] == originating_symbol_table
        self.free_vars[name] = originating_symbol_table

    def __repr__(self):
        return f"SymbolTable(local_vars={sorted(self.local_vars)}, free_vars={sorted(self.free_vars)}, cell_vars={sorted(self.cell_vars)}, global_vars={sorted(self.global_vars)})"

def determine_scopes(func_or_class, declared_outer, parent, symbol_tables):
    symbol_table = symbol_tables[func_or_class]
    symbol_table.set_parent(parent)

    if isinstance(func_or_class, Class):
        raise ValueError("can't do classes yet")
    elif isinstance(func_or_class, Function):
        # find all assignments - these are global variables
        for param in func_or_class.params:
            symbol_table.local_vars.add(param.content)
            # params shadow outer variables
            if param.content in declared_outer:
                declared_outer.remove(param.content)

        for stmt in func_or_class.body:
            for assign in find_all_assignments(stmt):
                if isinstance(assign.lhs, Token) and assign.lhs.kind == 'Variable':
                    symbol_table.local_vars.add(assign.lhs.content)

        for stmt in func_or_class.body:
            for lookup in find_all_variable_lookups(stmt):
                name = lookup.content
                if name in symbol_table.local_vars:
                    pass
                elif name in declared_outer:
                    declared_outer[name].mark_as_cell_var(name)

                    cur = symbol_table
                    while cur is not declared_outer[name]:
                        cur.mark_or_add_as_free_var(name, declared_outer[name])
                        cur = cur.parent

                else:
                    symbol_table.global_vars.add(name)

        declared = declared_outer.copy()
        for name in symbol_table.local_vars:  # no cellvars yet, if there were we'd add them too
            declared[name] = symbol_table

        for stmt in func_or_class.body:
            for nested_scope in find_all_nested_scopes(stmt):
                determine_scopes(nested_scope, declared, symbol_table, symbol_tables)
    else:
        raise ValueError(f"Expects classes and functions, not {func_or_class}")


def find_all_assignments(stmt):
    def is_assignment(node):
        return isinstance(node, Assignment)
    found = []
    find_all_in_tree(is_assignment, stmt, found)
    return found

def find_all_variable_lookups(stmt):
    def is_variable_loookup(node):
        return isinstance(node, Token) and node.kind == 'Variable'
    found = []
    find_all_in_tree(is_variable_loookup, stmt, found)
    return found

def find_all_nested_scopes(stmt):
    def is_nested_scope(node):
        return isinstance(node, (Function, Class))
    found = []
    find_all_in_tree(is_nested_scope, stmt, found)
    return found

def find_all_in_tree(condition, node, found):
    """Find all matching nodes in an AST without stepping into Func and Class bodies"""
    if condition(node):
        found.append(node)
    if isinstance(node, Token): pass
    elif isinstance(node, BinaryOp):
        find_all_in_tree(condition, node.left, found)
        find_all_in_tree(condition, node.right, found)
    elif isinstance(node, UnaryOp):
        find_all_in_tree(condition, node.right, round)
    elif isinstance(node, Function): pass
    elif isinstance(node, PropAccess): pass
    elif isinstance(node, Call):
        find_all_in_tree(condition, node.callable, found)
        for arg in node.arguments:
            find_all_in_tree(condition, arg, found)
    elif isinstance(node, (Run, Class, Compile)):
        pass
    elif isinstance(node, Return):
        find_all_in_tree(condition, node.expression, found)
    elif isinstance(node, Assignment):
        # no lhs yet because no property assignment to test it with
        #find_all_in_tree(condition, node.lhs, found)
        find_all_in_tree(condition, node.rhs, found)
    elif isinstance(node, If):
        for s in node.body:
            find_all_in_tree(condition, s, found)
        for s in node.else_body:
            find_all_in_tree(condition, s, found)
    elif isinstance(node, While):
        for s in node.body:
            find_all_in_tree(condition, s, found)
    else:
        raise ValueError(f"what is this: {repr(node)}")
