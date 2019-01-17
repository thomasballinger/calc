from collections import namedtuple

from tokens import Token, tokenize

BinaryOp = namedtuple('BinaryOp', ['left', 'op', 'right'])
UnaryOp = namedtuple('UnaryOp', ['op', 'right'])
Assignment = namedtuple('Assignment', ['variable', 'expression'])

def pprint_tree_small(node, indent=2):
    if isinstance(node, Token):
        print(' '*indent + str(node.content))
    elif isinstance(node, BinaryOp):
        print(' '*indent + node.op.content)
        pprint_tree(node.left, indent + 2)
        pprint_tree(node.right, indent + 2)
    elif isinstance(node, UnaryOp):
        print(' '*indent + node.op.content)
        pprint_tree(node.right, indent + 2)

def pprint_tree(node):
    print(pformat_full_tree(node))

def pformat_full_tree(node, indent=0):
    space = ' '*indent
    nl = '\n'
    if isinstance(node, Token):
        return(f"{repr(node)}")
    elif isinstance(node, BinaryOp):
        return(
                   f"BinaryOp(op={node.op},{nl}"
            f"{space}         left={pformat_full_tree(node.left, indent+9+5)}{nl}"
            f"{space}         right={pformat_full_tree(node.right, indent+9+6)})"
        )
    elif isinstance(node, UnaryOp):
        return(
                  f"UnaryOp(op={node.op},{nl}"
            f"{space}         left={pformat_full_tree(node.left, indent+8+5)}{nl}"
            f"{space}         right={pformat_full_tree(node.right, indent+8+6)})"
        )
    elif isinstance(node, Assignment):
        return(
                   f"Assignment({node.variable},{nl}"
            f"{space}           value={pformat_full_tree(node.expression, indent+9+6)})"
        )
    else:
        raise ValueError("Can't parse tree node: {}".format(node))

def start_end(node):
    if isinstance(node, Token):
        return (node.start, node.end)
    elif isinstance(node, BinaryOp):
        left_start, left_end= start_end(node.left)
        op_start, op_end = start_end(node.op)
        right_start, right_end = start_end(node.right)
        return (
            min([left_start, op_start, right_start]),
            max([left_end, op_end, right_end])
        )
    elif isinstance(node, UnaryOp):
        op_start, op_end = start_end(node.op)
        right_start, right_end = start_end(node.right)
        return (
            min([op_start, right_start]),
            max([op_end, right_end])
        )
    elif isinstance(node, Assignment):
        var_start, var_end = start_end(node.variable)
        expr_start, expr_end = start_end(node.expression)
        return (
            min([var_start, expr_start]),
            max([var_end, expr_end])
        )

def parse(remaining_tokens):
    stmts = []
    while remaining_tokens:
        stmt, remaining_tokens = parse_statement(remaining_tokens)
        stmts.append(stmt)
    return stmts

def parse_statement(tokens):
    if len(tokens) >= 2 and tokens[0].kind == 'Variable' and tokens[1].kind == 'Equals':
        stmt, remaining_tokens = parse_assignment_statement(tokens)
    else:
        stmt, remaining_tokens = parse_greater_or_less(tokens)
    if not remaining_tokens:
        raise ValueError("Expected semicolon after expression...")
    semi, *remaining_tokens = remaining_tokens
    assert semi.kind == 'Semi'
    return stmt, remaining_tokens

def parse_assignment_statement(tokens):
    var, equals, *remaining_tokens = tokens
    assert var.kind == 'Variable'
    assert equals.kind == 'Equals'
    expression, remaining_tokens = parse_greater_or_less(remaining_tokens)
    return Assignment(variable=var, expression=expression), remaining_tokens

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
    elif tokens[0].kind == 'Variable':
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

