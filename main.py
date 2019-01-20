#!/usr/bin/env python3

from collections import namedtuple
import sys
import time
from num2words import num2words
from tokens import Token, tokenize
from parse import BinaryOp, UnaryOp, pprint_tree, parse, Assignment, If, While, Call, Return, Function, Run
from typeinfer import type_infer_program
from linter import lint_program
from completer import completer

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

def execute_program(stmts, variables):
    for stmt in stmts:
        execute(stmt, variables)

def execute(stmt, variables):
    if isinstance(stmt, (BinaryOp, UnaryOp, Token, Call)):
        value = evaluate(stmt, variables)
        if DEBUG: print('expr in expr stmt evaled to:', value)
    elif isinstance(stmt, Assignment):
        value = evaluate(stmt.expression, variables)
        variables.set(stmt.variable.content, value)
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
    elif isinstance(node, Call):
        f = evaluate(node.callable, variables)
        args = [evaluate(expr, variables) for expr in node.arguments]
        if type(f) == type(lambda: None):
            return f(*args)
        else:
            f.execute(args)
            return None
            #raise ValueError("Don't know how to evaluate: {}".format(node))

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

def debug_repl():
    global DEBUG
    DEBUG = False
    import readline, os
    histfile = os.path.join(os.path.expanduser("~"), ".calchist")
    try:
        readline.read_history_file(histfile)
        readline.set_history_length(1000)
    except IOError:
        pass
    import atexit
    atexit.register(readline.write_history_file, histfile)

    readline.parse_and_bind("tab: complete")
    readline.set_completer(completer)
    builtin_scope = Scope()
    for name in builtin_funcs:
        builtin_scope.set(name, builtin_funcs[name])
    variables = builtin_scope.create_child_scope()
    DEBUG = True
    tokens = []
    lines = 0
    prompt = '>'
    while True:
        try:
            s = input(prompt + ' ')
        except KeyboardInterrupt as e:
            if tokens:
                tokens, prompt = [], '>'
                print('input cleared')
                continue
            else:
                raise e

        if s == '' and tokens:
            debug_exec(tokens, variables)
            tokens, prompt = [], '>'
        elif s and not tokens:
            tokens = tokenize(s)
            try:
                parse(tokens)
            except:
                prompt = '...'
            else:
                debug_exec(tokens, variables)
                tokens, prompt = [], '>'
        elif s and tokens:
            tokens += tokenize(s)

def debug_exec(tokens, variables):
    import traceback
    try:
        print('tokens:', ' '.join(str(tok.content) for tok in tokens))
        stmts = parse(tokens)
        print('AST of each statement:')
        for stmt in stmts:
            pprint_tree(stmt)
        execute_program(stmts, variables)
    except ValueError as e:
        print(e)
    except AssertionError as e:
        traceback.print_exc()
    except CantFindVariable as e:
        print(e)

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

if __name__ == "__main__":
    #import doctest
    #doctest.testmod()

    args = sys.argv[1:]
    if len(args) == 1:
        run_program(open(args[0]).read())
    else:
        debug_repl()
