from collections import namedtuple

from tokens import Token, tokenize

BinaryOp = namedtuple('BinaryOp', ['left', 'op', 'right'])
UnaryOp = namedtuple('UnaryOp', ['op', 'right'])

def pprint_tree(node, indent=2):
    if isinstance(node, Token):
        print(' '*indent + str(node.content))
    elif isinstance(node, BinaryOp):
        print(' '*indent + node.op.content)
        pprint_tree(node.left, indent + 2)
        pprint_tree(node.right, indent + 2)
    elif isinstance(node, UnaryOp):
        print(' '*indent + node.op.content)
        pprint_tree(node.right, indent + 2)

def parse(remaining_tokens):
    stmts = []
    while remaining_tokens:
        stmt, remaining_tokens = parse_statement(remaining_tokens)
        stmts.append(stmt)
    return stmts

def parse_statement(tokens):
    stmt, remaining_tokens = parse_greater_or_less(tokens)
    semi, *remaining_tokens = remaining_tokens
    assert semi.kind == 'Semi'
    return stmt, remaining_tokens

def parse_greater_or_less(tokens):
    expr, remaining_tokens = parse_plus_or_minus(tokens)

    if remaining_tokens and remaining_tokens[0].kind in ('Greater', 'Less'):
        op, *remaining_tokens = remaining_tokens
        right, remaining_tokens = parse_plus_or_minus(remaining_tokens)
        expr = BinaryOp(expr, op, right)

    return expr, remaining_tokens

def parse_plus_or_minus(tokens):
    expr, remaining_tokens = parse_multiply_or_divide(tokens)

    while remaining_tokens and remaining_tokens[0].kind in ('Plus', 'Minus'):
        op, *remaining_tokens = remaining_tokens
        right, remaining_tokens = parse_multiply_or_divide(remaining_tokens)
        expr = BinaryOp(expr, op, right)

    return expr, remaining_tokens

def parse_multiply_or_divide(tokens):
    expr, remaining_tokens = parse_operand(tokens)

    while remaining_tokens and remaining_tokens[0].kind in ('Star', 'Slash'):
        op, *remaining_tokens = remaining_tokens
        right, remaining_tokens = parse_operand(remaining_tokens)
        expr = BinaryOp(expr, op, right)

    return expr, remaining_tokens

def parse_unary_op(tokens):
    op, *remaining_tokens = tokens
    assert op.kind in ('Plus', 'Minus', 'Print', 'String', 'Length')
    operand, remaining_tokens = parse_operand(remaining_tokens)
    expr = UnaryOp(op=op, right=operand)

    return expr, remaining_tokens

def parse_operand(tokens):
    if tokens[0].kind == 'Number':
        expr, *remaining_tokens = tokens
        return expr, remaining_tokens
    elif tokens[0].kind in ('Minus', 'Plus', 'Print', 'String', 'Length'):
        expr, remaining_tokens = parse_unary_op(tokens)
        return expr, remaining_tokens
    elif tokens[0].kind == 'Left Paren':
        _, *remaining_tokens = tokens
        expr, remaining_tokens = parse_greater_or_less(remaining_tokens)
        right_paren, *remaining_tokens = remaining_tokens
        if not right_paren.kind == 'Right Paren':
            raise ValueError('Expected {} to be a right paren'.format(right_paren))
        return expr, remaining_tokens
    else:
        raise ValueError("Can't parse tokens: {}".format(tokens))

