from parse import BinaryOp, UnaryOp, pprint_tree, parse, Assignment, If, While, Call, Return, Function, Run, PropAccess, Class, Compile
from tokens import Token, tokenize
import time

from num2words import num2words

DEBUG = False

binary_op_funcs = {
    'Plus': lambda x, y: x+y,
    'Minus': lambda x, y: x-y,
    'Star': lambda x, y: x*y,
    'Slash': lambda x, y: x/y,
    'Percent': lambda x, y: x%y,
    'Greater': lambda x, y: x > y,
    'Less': lambda x, y: x < y,
    'Equals Equals': lambda x, y: x == y,
}
unary_op_funcs = {
    'plus': lambda x: x,
    'minus': lambda x: -x,
}
builtin_funcs = {
    'print': lambda x: (print(x), x)[1],
    'string': num2words,
    'length': len,
}

class CalcReturnException(Exception):
    def __init__(self, value):
        self.value = value

class CantFindVariable(KeyError): pass

class Scope:
    def create_child_scope(self):
        return Scope(parent=self)

    def __init__(self, parent=None):
        self.bindings = {}
        self.parent = parent

    def get(self, name):
        cur = self
        while cur is not None:
            if name in cur.bindings:
                return cur.bindings[name]
            cur = cur.parent
        raise CantFindVariable(f"Name '{name}' not found in scopes")

    def set(self, name, value):
        cur, i = self, 0
        while cur is not None:
            if name in cur.bindings:
                if DEBUG:
                    if i == 0: scope = 'local scope'
                    elif cur.parent is None: scope = 'global scope'
                    else: scope = 'outer scope number ' + str(i)
                    print('setting', name, 'to', value, 'in', scope)
                cur.bindings[name] = value
                return
            cur, i = cur.parent, i + 1

        # create new variable if none found
        if DEBUG:
            print('creating new variable', name, 'in local scope and setting to', value)
        self.bindings[name] = value

    def __repr__(self):
        if self.parent is None:
            return f"Scope({repr(self.bindings)})"
        else:
            return f"Scope({repr(self.bindings)}, parent=\n{repr(self.parent)})"

class Closure:
    """Code and state, living happily together."""
    def __init__(self, function_ast, parent_scope):
        self.function_ast = function_ast
        self.parent_scope = parent_scope

    def execute(self, args):
        if len(args) != len(self.function_ast.params):
            raise ValueError("bad arity")
        new_scope = self.parent_scope.create_child_scope()
        for param, arg in zip(self.function_ast.params, args):
            new_scope.set(param.content, arg)
        for stmt in self.function_ast.body:
            execute(stmt, new_scope)
        return None

class MethodWrapper:
    def __init__(self, func, instance):
        self.func = func
        self.instance = instance

    def execute(self, args):
        all_args = [self.instance] + args
        return self.func.execute(all_args)


class ClassObj:
    def __init__(self, name, scope, extends=None):
        self.name = name
        self.scope = scope
        self.extends = extends
    def prop_access(self, name):
        raise ValueError("Don't know how to get props on class")
    def prop_assign(self, name, value):
        raise ValueError("Don't know how to assign to class")
    def create_instance(self):
        raise ValueError("Don't know how to create instance")

    def get_for_instance(self, instance):
        return 

class Instance:
    def prop_access(self, name):
        raise ValueError("Don't know how to get prop on instance")
    def prop_assign(self, name, value):
        raise ValueError("Don't know how to assign to instance")

def execute_program(stmts, variables):
    for stmt in stmts:
        execute(stmt, variables)

def execute(stmt, variables):
    if isinstance(stmt, (BinaryOp, UnaryOp, Token, Call)):
        value = evaluate(stmt, variables)
        if DEBUG: print('expr in expr stmt evaled to:', value)
    elif isinstance(stmt, Assignment):
        value = evaluate(stmt.rhs, variables)
        if isinstance(stmt.lhs, PropAccess):
            left = evaluate(stmt.lhs.left, variables)
            left.prop_set(value)
        elif stmt.lhs.kind == 'Variable':
            variables.set(stmt.lhs.content, value)
        else:
            raise AssertionError(f'bad assignment statement: {stmt.lhs}')
    elif isinstance(stmt, If):
        value = evaluate(stmt.condition, variables)
        if value:
            for s in stmt.body:
                execute(s, variables)
        else:
            for s in stmt.else_body:
                execute(s, variables)
    elif isinstance(stmt, While):
        while evaluate(stmt.condition, variables):
            for s in stmt.body:
                execute(s, variables)
    elif isinstance(stmt, Run):
        filename = stmt.filename.content + '.calc'
        if DEBUG: print(f'Executing {filename}...')
        with DebugModeOff():
            t0 = time.time()
            s = open(filename).read()
            run_program(s, with_scope=variables)
            t = time.time() - t0
        if DEBUG: print(f'...done in {t:.5f}s')
    elif isinstance(stmt, Return):
        value = evaluate(stmt.expression, variables)
        raise CalcReturnException(value)
    elif isinstance(stmt, Class):
        cls_variables = variables.create_child_scope()
        cls = ClassObj(stmt.name, cls_variables, stmt.extends)
        for s in stmt.body:
            execute(s, cls_variables)
        print('seting', stmt.name, ' to', cls)
        variables.set(stmt.name.content, cls)

def evaluate(node, variables):
    if isinstance(node, Token):
        if node.kind == 'Number':
            return node.content
        elif node.kind == 'Variable':
            return variables.get(node.content)
        elif node.kind == 'String':
            return node.content
    elif isinstance(node, BinaryOp):
        return binary_op_funcs[node.op.kind](evaluate(node.left, variables), evaluate(node.right, variables))
    elif isinstance(node, UnaryOp):
        return unary_op_funcs[node.op.kind](evaluate(node.right, variables))
    elif isinstance(node, Function):
        return Closure(node, variables)
    elif isinstance(node, PropAccess):
        raise ValueError("Don't know how to evaluate PropAccess")
    elif isinstance(node, Call):
        f = evaluate(node.callable, variables)
        args = [evaluate(expr, variables) for expr in node.arguments]
        if type(f) == type(lambda: None):
            return f(*args)
        elif isinstance(f, Closure):
            try:
                f.execute(args)
            except CalcReturnException as e:
                return e.value
            else:
                return None
        elif isinstance(f, Class):
            return f.create_instance()
            raise ValueError("Don't know how to call a class")
        else:
            raise ValueError("Don't know how to evaluate: {}".format(node))

class DebugModeOn:
    def __enter__(self):
        global DEBUG
        DEBUG = True
    def __exit__(self, *args):
        global DEBUG
        DEBUG = False

class DebugModeOff:
    def __enter__(self):
        global DEBUG
        self.orig = DEBUG
        DEBUG = False
    def __exit__(self, *args):
        global DEBUG
        DEBUG = self.orig

def run_program(source, with_scope=None):
    """
    >>> run_program("print(1); print(2 + 3);")
    1
    5
    """
    tokens = tokenize(source)
    stmts = parse(tokens)
    if with_scope:
        variables = with_scope
    else:
        builtin_scope = Scope()
        for name in builtin_funcs:
            builtin_scope.set(name, builtin_funcs[name])
        variables = builtin_scope.create_child_scope()
    execute_program(stmts, variables)

