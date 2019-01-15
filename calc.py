from collections import namedtuple
from num2words import num2words
from tokens import Token, tokenize
from parse import BinaryOp, UnaryOp, pprint_tree, parse

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

def execute(stmt):
    if isinstance(stmt, (BinaryOp, UnaryOp, Token)):
        value = evaluate(stmt)

def evaluate(node):
    if isinstance(node, Token):
        return node.content
    elif isinstance(node, BinaryOp):
        return binary_funcs[node.op.kind](evaluate(node.left), evaluate(node.right))
    elif isinstance(node, UnaryOp):
        return unary_funcs[node.op.kind](evaluate(node.right))

def debug_repl():
    while True:
        try:
            s = input('> ')
            tokens = tokenize(s)
            print(repr(tokens))
            stmts = parse(tokens)
            print(repr(stmts))
            pprint_tree(stmts)
            for stmt in stmts:
                execute(stmt)
            #print(evaluate(stmts))
        except ValueError as e:
            print(e)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
    debug_repl()
