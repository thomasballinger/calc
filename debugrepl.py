#!/usr/bin/env python3

from collections import namedtuple
import sys
import time
from tokens import Token, tokenize
from parse import BinaryOp, UnaryOp, pprint_tree, parse, Assignment, If, While, Call, Return, Function, Run, PropAccess, Class
from typeinfer import type_infer_program
from linter import lint_program
from completer import completer
from interp import Scope, builtin_funcs, execute_program, CantFindVariable, run_program
import interp

def debug_repl():
    interp.DEBUG = False
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
    interp.DEBUG = True
    tokens = []
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

if __name__ == "__main__":
    #import doctest
    #doctest.testmod()

    args = sys.argv[1:]
    if len(args) == 1:
        run_program(open(args[0]).read())
    else:
        debug_repl()
