from parse import BinaryOp, UnaryOp, pprint_tree, parse, Assignment, Token, start_end

def lint(node):
    """Returns True if there was a problem"""
    # TODO: make this function lint for something more useful!
    # Returns True if there's a 7 anywhere
    if isinstance(node, Token):
        if node.kind == 'Number' and node.content == 7:
            return (node.start, node.end)
    elif isinstance(node, BinaryOp):
        sevens_on_left = lint(node.left)
        sevens_on_right = lint(node.right)
        return sevens_on_left or sevens_on_right
    elif isinstance(node, UnaryOp):
        sevens_on_right = lint(node.right)
        return sevens_on_right

def lint_program(stmts, source):
    for stmt in stmts:
        expr_start, expr_end = start_end(stmt)
        if isinstance(stmt, (BinaryOp, UnaryOp, Token)):
            problem = lint(stmt)
        elif isinstance(stmt, Assignment):
            problem = lint(stmt.expression)

        if problem:
            start, end = problem
            excerpt = source[start:end]
            front_context = source[start-5:start]
            back_context = source[end:start+5]
            nl = '\n'
            print('problem with expression', source[expr_start:expr_end])
            print(
                         f"{front_context}{excerpt}{back_context}{nl}"
               f"{' '* len(front_context)}{'^'*len(excerpt)}{nl}"
                "problem found in this expression!")
