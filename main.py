#!/usr/bin/env python3

from collections import namedtuple
import sys
from num2words import num2words
from tokens import Token, tokenize
from parse import BinaryOp, UnaryOp, pprint_tree, parse, Assignment, If, While, Call, Return, Function
from typeinfer import type_infer_program
from linter import lint_program
from completer import completer

binary_op_funcs = {
    'Plus': lambda x, y: x+y,
    'Minus': lambda x, y: x-y,
    'Star': lambda x, y: x*y,
    'Slash': lambda x, y: x/y,
    'Greater': lambda x, y: x > y,
    'Less': lambda x, y: x < y,
}
builtin_funcs = {
    'plus': lambda x: x,
    'minus': lambda x: -x,
    'print': lambda x: (print(x), x)[1],
    'string': num2words,
    'length': len,
}

class Scope:
    def create_child_scope(self):
        return Scope(parent=self)

    def __init__(self, parent=None):
        self.bindings = {}
        self.parent = parent

    def get(self, name):
        return self.bindings[name]

    def set(self, name, value):
        self.bindings[name] = value

    def __repr__(self):
        if self.parent is None:
            return f"Scope({repr(self.bindings)})"
        else:
            return f"Scope({repr(self.bindings)}, parent=\n{repr(self.parent)})"


def execute_program(stmts, variables, debug=False):
    for stmt in stmts:
        execute(stmt, variables, debug=debug)

def execute(stmt, variables, debug=False):
    if isinstance(stmt, (BinaryOp, UnaryOp, Token, Call)):
        value = evaluate(stmt, variables)
        if debug: print('expr in expr stmt evaled to:', value)
    elif isinstance(stmt, Assignment):
        value = evaluate(stmt.expression, variables)
        if debug: print('setting', stmt.variable.content, 'to', value)
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

def evaluate(node, variables):
    if isinstance(node, Token):
        if node.kind == 'Number':
            return node.content
        elif node.kind == 'Variable':
            print(f'looking up {node.content}, got {variables.get(node.content)}')
            return variables.get(node.content)
    elif isinstance(node, BinaryOp):
        return binary_op_funcs[node.op.kind](evaluate(node.left, variables), evaluate(node.right, variables))
    elif isinstance(node, UnaryOp):
        return unary_funcs[node.op.kind](evaluate(node.right, variables))
    elif isinstance(node, Function):
        return node;
    elif isinstance(node, Call):
        f = evaluate(node.callable, variables)
        args = [evaluate(expr, variables) for expr in node.arguments]
        if type(f) == type(lambda: None):
            return f(*args)
        else:
            new_scope = variables.create_child_scope()
            for param, arg in zip(f.params, args):
                new_scope.set(param.content, arg)
            for stmt in f.body:
                execute(stmt, new_scope)
            return None
            #raise ValueError("Don't know how to evaluate: {}".format(node))

def debug_repl():
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
    variables = Scope()
    for name in builtin_funcs:
        variables.set(name, builtin_funcs[name])
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
        print('running program...')
        execute_program(stmts, variables, debug=True)
        print('global symbol table at end of program:\n', repr(variables))
    except ValueError as e:
        print(e)
    except AssertionError as e:
        traceback.print_exc()
    except KeyError as e:
        print('bad lookup of variable', e)

def run_program(source):
    """
    >>> run_program("print(1); print(2 + 3);")
    1
    5
    """
    tokens = tokenize(source)
    stmts = parse(tokens)
    variables = {}
    execute_program(stmts, variables)

if __name__ == "__main__":
    #import doctest
    #doctest.testmod()

    args = sys.argv[1:]
    if len(args) == 1:
        run_program(open(args[0]).read())
    else:
        debug_repl()
