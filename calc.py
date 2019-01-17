from collections import namedtuple
from num2words import num2words
from tokens import Token, tokenize
from parse import BinaryOp, UnaryOp, pprint_tree, parse, Assignment

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
signatures = {
    ('Plus', int, int): int,
    ('Plus', str, str): str,
    ('Print', str): str,
    ('Print', int): int,
    ('Minus', int, int): int,
    ('Minus', int): int,
    ('Plus', int): int,
    ('Star', int, int): int,
    ('Slash', int, int): int,
    ('Greater', int, int): bool,
    ('Less', int, int): bool,
    ('String', int): str,
}

def execute(stmt, variables):
    if isinstance(stmt, (BinaryOp, UnaryOp, Token)):
        print(type_infer(stmt))
        evaluate(stmt, variables)
    elif isinstance(stmt, Assignment):
        value = evaluate(stmt.expression, variables)
        print('set', stmt.variable.content, 'to', value)
        variables[stmt.variable.content] = value

def type_infer(node):
    if isinstance(node, Token):
        if node.kind == 'Number': return int
    elif isinstance(node, BinaryOp):
        left_type = type_infer(node.left)
        right_type = type_infer(node.right)
        result_type = signatures[(node.op.kind, left_type, right_type)]
        return result_type
    elif isinstance(node, UnaryOp):
        expression_type = type_infer(node.right)
        result_type = signatures[(node.op.kind, expression_type)]
        return result_type


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
            print(repr(tokens))
            stmts = parse(tokens)
            print(repr(stmts))
            pprint_tree(stmts)
            for stmt in stmts:
                execute(stmt, variables)
            print(variables)
        except ValueError as e:
            print(e)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
    debug_repl()
