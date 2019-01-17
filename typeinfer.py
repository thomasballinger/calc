from parse import BinaryOp, UnaryOp, pprint_tree, parse, Assignment, Token, start_end

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

def type_infer_program(stmts, source):
    for stmt in stmts:
        start, end = start_end(stmt)
        if isinstance(stmt, (BinaryOp, UnaryOp, Token)):
            inferred_type = type_infer(stmt)
            print(source[start:end], '<------ inferred type: ', inferred_type)
        elif isinstance(stmt, Assignment):
            inferred_type = type_infer(stmt.expression)
            print(source[start:end], '<------ inferred type of expression: ', inferred_type)
