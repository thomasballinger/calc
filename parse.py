from collections import namedtuple

from tokens import Token, tokenize


BinaryOp = namedtuple('BinaryOp', ['left', 'op', 'right'])
UnaryOp = namedtuple('UnaryOp', ['op', 'right'])
Assignment = namedtuple('Assignment', ['variable', 'expression'])
If = namedtuple('If', ['condition', 'body', 'else_body'])
While = namedtuple('While', ['condition', 'body'])
Call = namedtuple('Call', ['callable', 'arguments'])
Return = namedtuple('Return', ['expression'])
Function = namedtuple('Function', ['params', 'body'])
Run = namedtuple('Run', ['filename'])

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
            f"{space}         right={pformat_full_tree(node.right, indent+8+6)})"
        )
    elif isinstance(node, Assignment):
        return(
                   f"Assignment(variable={node.variable},{nl}"
            f"{space}           value={pformat_full_tree(node.expression, indent+11+6)})"
        )
    elif isinstance(node, Call):
        s =             f"Call(callable={node.callable},{nl}"
        if len(node.arguments) == 0:
            s += f"{space}     arguments=[])"
        elif len(node.arguments) == 1:
            s += f"{space}     arguments=[{pformat_full_tree(node.arguments[0], indent+16)}])"
        else:
            s += f"{space}     arguments=[{pformat_full_tree(node.arguments[0], indent+16)},{nl}"
        for argument in node.arguments[1:-1]:
            s += f"{space}                {pformat_full_tree(argument, indent+16)},{nl}"
        if len(node.arguments) > 1:
            s += f"{space}                {pformat_full_tree(node.arguments[-1], indent+16)}])"
        return s
    elif isinstance(node, Function):
        s = f"Function(params=({', '.join(v.content for v in node.params)}),{nl}"
        s += pformat_body('body', node.body, indent=indent+9)
        s += ')'
        return s
    elif isinstance(node, If):
        s = f"If(cond={pformat_full_tree(node.condition, indent+3+5)},{nl}"
        s += pformat_body('body', node.body, indent=indent+3)
        if node.else_body:
            s += '\n'
            s += pformat_body('else_body', node.else_body, indent=indent+3)
        s += ')'
        return s
    elif isinstance(node, While):
        s = f"While(cond={pformat_full_tree(node.condition, indent+6+5)},{nl}"
        s += pformat_body('body', node.body, indent=indent+6)
        s += ')'
        return s
    elif isinstance(node, Run):
        return f"Run(filename={node.filename})"
    else:
        raise ValueError("Can't display tree node: {}".format(node))

def pformat_body(body_name, statements, indent=0):
    space = ' ' * indent
    s = ''
    nl = '\n'
    if len(statements) == 0:
        s += f"{space}{body_name}=[])"
    elif len(statements) == 1:
        s += f"{space}{body_name}=[{pformat_full_tree(statements[0], indent+len(body_name)+2)}]"
    else:
        s += f"{space}{body_name}=[{pformat_full_tree(statements[0], indent+len(body_name)+2)},{nl}"
    for statement in statements[1:-1]:
        s += f"{space}{' '*len(body_name)}  {pformat_full_tree(statement, indent+len(body_name)+2)},{nl}"
    if len(statements) > 1:
        s += f"{space}{' '*len(body_name)}  {pformat_full_tree(statements[-1], indent+len(body_name)+2)}])"
    return s

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
    elif tokens and tokens[0].kind == 'If':
        stmt, remaining_tokens = parse_if_statement(tokens)
    elif tokens and tokens[0].kind == 'While':
        stmt, remaining_tokens = parse_while_statement(tokens)
    elif tokens and tokens[0].kind == 'Return':
        stmt, remaining_tokens = parse_return_statement(tokens)
    elif tokens and tokens[0].kind == 'Run':
        stmt, remaining_tokens = parse_run_statement(tokens)
    else:
        stmt, remaining_tokens = parse_expression(tokens)
    if not remaining_tokens:
        raise ValueError("Expected semicolon after expression...")
    semi, *remaining_tokens = remaining_tokens
    assert semi.kind == 'Semi', semi
    return stmt, remaining_tokens

def parse_run_statement(tokens):
    run, filename, *remaining_tokens = tokens
    assert run.kind == 'Run'
    return Run(filename=filename), remaining_tokens

def parse_assignment_statement(tokens):
    var, equals, *remaining_tokens = tokens
    assert var.kind == 'Variable'
    assert equals.kind == 'Equals'
    expression, remaining_tokens = parse_expression(remaining_tokens)
    return Assignment(variable=var, expression=expression), remaining_tokens

def parse_if_statement(tokens):
    """
    >>> parse_if_statement(tokenize('if foo then bar; else baz; end'))[0]
    If(condition=Token(kind='Variable', content='foo'), body=[Token(kind='Variable', content='bar')], else_body=[Token(kind='Variable', content='baz')])
    """
    if_, *remaining_tokens = tokens
    assert if_.kind == 'If', if_.kind
    condition, remaining_tokens = parse_expression(remaining_tokens)
    then, *remaining_tokens = remaining_tokens
    assert then.kind == 'Then'
    statements = []
    else_statements = []
    while remaining_tokens[0].kind not in ('Else', 'End'):
        stmt, remaining_tokens = parse_statement(remaining_tokens)
        statements.append(stmt)
    end_or_else, *remaining_tokens = remaining_tokens
    if end_or_else.kind == 'Else':
        while remaining_tokens[0].kind not in ('End'):
            stmt, remaining_tokens = parse_statement(remaining_tokens)
            else_statements.append(stmt)
        end, *remaining_tokens = remaining_tokens
    return If(condition=condition, body=statements, else_body=else_statements), remaining_tokens

def parse_while_statement(tokens):
    while_, *remaining_tokens = tokens
    assert while_.kind == 'While', if_.kind
    condition, remaining_tokens = parse_expression(remaining_tokens)
    do, *remaining_tokens = remaining_tokens
    assert do.kind == 'Do'
    statements = []
    while remaining_tokens[0].kind not in ('End'):
        stmt, remaining_tokens = parse_statement(remaining_tokens)
        statements.append(stmt)
    end, *remaining_tokens = remaining_tokens
    return While(condition=condition, body=statements), remaining_tokens

def parse_return_statement(tokens):
    return_, *remaining_tokens = tokens
    if remaining_tokens[0].kind == 'Semi':
        return Return(expresssion=None), remaining_tokens
    expression, remaining_tokens = parse_expression(remaining_tokens)
    return Return(expresssion=expression), remaining_tokens

def parse_expression(tokens):
    return parse_greater_or_less(tokens)

def parse_greater_or_less(tokens):
    expr, remaining_tokens = parse_plus_or_minus(tokens)

    if remaining_tokens and remaining_tokens[0].kind in ('Greater', 'Less'):
        op, *remaining_tokens = remaining_tokens
        right, remaining_tokens = parse_plus_or_minus(remaining_tokens)
        expr = BinaryOp(expr, op, right)

    elif (remaining_tokens[1:2] and remaining_tokens[0].kind == remaining_tokens[1].kind == 'Equals'):
        eq1, eq2, *remaining_tokens = remaining_tokens
        op = Token(kind='Equals Equals', content='==', start=eq1.start, end=eq2.end)
        assert eq1.kind == 'Equals' and eq2.kind == 'Equals'
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
    expr, remaining_tokens = parse_unary_op(tokens)

    while remaining_tokens and remaining_tokens[0].kind in ('Star', 'Slash', 'Percent'):
        op, *remaining_tokens = remaining_tokens
        right, remaining_tokens = parse_unary_op(remaining_tokens)
        expr = BinaryOp(expr, op, right)

    return expr, remaining_tokens

def parse_unary_op(tokens):
    op = None
    if tokens[0] in ('Plus', 'Minus'):
        op, *tokens = tokens
        expr, tokens = parse_unary_op(tokens)
        return tokens, UnaryOp(op=op, right=expr)
    return parse_call(tokens)

def parse_call(tokens):
    """
    >>> parse_call(tokenize('a()'))[0]
    Call(callable=Token(kind='Variable', content='a'), arguments=[])
    >>> parse_call(tokenize('a()(1)'))[0]
    Call(callable=Call(callable=Token(kind='Variable', content='a'), arguments=[]), arguments=[Token(kind='Number', content=1)])
    """
    expr, remaining_tokens = parse_primary(tokens)
    while remaining_tokens and remaining_tokens[0].kind == 'Left Paren':
        left_paren, *remaining_tokens = remaining_tokens
        assert left_paren.kind == 'Left Paren'
        arguments = []
        if remaining_tokens[0].kind != 'Right Paren':
            argument, remaining_tokens = parse_expression(remaining_tokens)
            arguments.append(argument)
            while remaining_tokens[0].kind != 'Right Paren':
                comma, *remaining_tokens = remaining_tokens
                assert comma.kind == 'Comma'
                argument, remaining_tokens = parse_expression(remaining_tokens)
                arguments.append(argument)
        right_paren, *remaining_tokens = remaining_tokens
        assert right_paren.kind == 'Right Paren'
        expr = Call(callable=expr, arguments=arguments)
    return expr, remaining_tokens

def parse_primary(tokens):
    """
    >>> parse_primary(tokenize('1'))
    (Token(kind='Number', content=1), [])
    >>> parse_primary(tokenize('abc;'))
    (Token(kind='Variable', content='abc'), [Token(kind='Semi')])
    """
    if tokens[0].kind == 'Number':
        expr, *remaining_tokens = tokens
        return expr, remaining_tokens
    elif tokens[0].kind == 'Variable':
        expr, *remaining_tokens = tokens
        return expr, remaining_tokens
    elif tokens[0].kind == 'String':
        expr, *remaining_tokens = tokens
        return expr, remaining_tokens
    elif tokens[0].kind == 'Left Paren' and tokens[1].kind == 'Right Paren':
        return parse_function(tokens)  # the 0 params case
    elif tokens[0].kind == 'Left Paren':
        left_paren, *remaining_tokens = tokens
        expr, remaining_tokens = parse_expression(remaining_tokens)
        if remaining_tokens[0].kind == 'Comma':
            assert expr.kind == 'Variable'
            return parse_function(tokens)  # the >1 params case, a backtrack
        right_paren, *remaining_tokens = remaining_tokens
        if not right_paren.kind == 'Right Paren':
            raise ValueError('Expected {} to be a right paren'.format(right_paren))
        if len(remaining_tokens) >= 2 and remaining_tokens[0].kind == 'Equals' and remaining_tokens[1].kind == 'Greater':
            assert expr.kind == 'Variable'
            return parse_function(tokens)  # the 1 param case, a backtrack
        return expr, remaining_tokens
    else:
        raise ValueError("Can't parse tokens: {}".format(tokens))

def parse_function(tokens):
    """
    >>> parse_function(tokenize('() => end'))[0]
    Function(params=[], body=[])
    >>> parse_function(tokenize('(x, y) => a; end'))[0]
    Function(params=[Token(kind='Variable', content='x'), Token(kind='Variable', content='y')], body=[Token(kind='Variable', content='a')])

    """
    left_paren, *remaining_tokens = tokens
    parameters = []
    if remaining_tokens[0].kind != 'Right Paren':
        variable, remaining_tokens = parse_primary(remaining_tokens)
        parameters.append(variable)
    while remaining_tokens[0].kind != 'Right Paren':
        comma, *remaining_tokens = remaining_tokens
        assert comma.kind == 'Comma', comma
        variable, remaining_tokens = parse_primary(remaining_tokens)
        parameters.append(variable)

    right_paren, equals, greater, *remaining_tokens = remaining_tokens
    assert (right_paren.kind == 'Right Paren' and equals.kind == 'Equals' and
            greater.kind == 'Greater'), (right_paren, equals, greater)

    statements = []
    while remaining_tokens[0].kind not in ('End'):
        stmt, remaining_tokens = parse_statement(remaining_tokens)
        statements.append(stmt)
    end, *remaining_tokens = remaining_tokens
    return Function(params=parameters, body=statements), remaining_tokens


if __name__ == '__main__':
    #toks = tokenize('while x < 4 do x = x + 1; end;')
    #import pudb; pudb.set_trace();
    #parse_while_statement(toks)
    import doctest
    doctest.testmod()
