from collections import namedtuple
import sys
from num2words import num2words
from tokens import Token, tokenize
from parse import BinaryOp, UnaryOp, pprint_tree, parse, Assignment
from typeinfer import type_infer_program

binary_funcs = {
    'Plus': lambda x, y: x+y,
    'Minus': lambda x, y: x-y,
    'Star': lambda x, y: x*y,
    'Slash': lambda x, y: x/y,
    'Greater': lambda x, y: x > y,
    'Less': lambda x, y: x < y,
}
unary_funcs = {
    'Plus': lambda x: x,
    'Minus': lambda x: -x,
    'Print': lambda x: (print(x), x)[1],
    'String': num2words,
    'Length': len,
}

def execute_program(stmts, variables):
    for stmt in stmts:
        execute(stmt, variables)

def execute(stmt, variables):
    if isinstance(stmt, (BinaryOp, UnaryOp, Token)):
        evaluate(stmt, variables)
    elif isinstance(stmt, Assignment):
        value = evaluate(stmt.expression, variables)
        print('setting', stmt.variable.content, 'to', value)
        variables[stmt.variable.content] = value

def evaluate(node, variables):
    if isinstance(node, Token):
        return node.content
    elif isinstance(node, BinaryOp):
        return binary_funcs[node.op.kind](evaluate(node.left, variables), evaluate(node.right, variables))
    elif isinstance(node, UnaryOp):
        return unary_funcs[node.op.kind](evaluate(node.right, variables))
    elif isinstance(node, Variable):
        return variables[node.content]

def debug_repl():
    variables = {}
    while True:
        try:
            s = input('> ')
            tokens = tokenize(s)
            print('tokens:', repr(tokens))
            stmts = parse(tokens)
            print('AST of each statement:')
            for stmt in stmts:
                pprint_tree(stmt)
            print("type inferring program...")
            type_infer_program(stmts, s)
            print('running program...')
            execute_program(stmts, variables)
            print('global symbol table at end of program:', variables)
        except ValueError as e:
            print(e)

def run_program(source):
    """
    >>> run_program("p 1; p (2 + 3);")
    1
    5
    """
    tokens = tokenize(source)
    stmts = parse(tokens)
    variables = {}
    execute_program(stmts, variables)

if __name__ == "__main__":
    import doctest
    doctest.testmod()

    args = sys.argv[1:]
    if len(args) == 1:
        run_program(open(args[0]).read())
    else:
        debug_repl()
