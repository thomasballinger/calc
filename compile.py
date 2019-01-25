from tokens import Token, tokenize
from parse import BinaryOp, UnaryOp, pprint_tree, parse, Assignment, If, While, Call, Return, Function, Run, PropAccess, Class, Compile, parse_expression
from scope_analysis import ScopeAnalyzer
from mutablecode import MutableCode

import sys
import opcode
import os

TOKEN_TO_BINOP = {
    '*': 'BINARY_MULTIPLY',
    '%': 'BINARY_MODULO',
    '+': 'BINARY_ADD',
    '-': 'BINARY_SUBTRACT',
    '/': 'BINARY_TRUE_DIVIDE',
    '<': ('COMPARE_OP', opcode.cmp_op.index('<')),
    '>': ('COMPARE_OP', opcode.cmp_op.index('>')),
    '==': ('COMPARE_OP', opcode.cmp_op.index('==')),
}

def compile_expression(node, code):
    if isinstance(node, Token):
        if node.kind == 'Number':
            n = code.register_const(node.content)
            code.add_op(('LOAD_CONST', n), node.lineno)
            return code
        elif node.kind == 'Variable':
            code.add_load_var_op(node.content, node.lineno)
            return code
        elif node.kind == 'String':
            n = code.register_const(node.content)
            code.add_op(('LOAD_CONST', n), node.lineno)
            return code

    elif isinstance(node, BinaryOp):
        compile_expression(node.left, code)
        compile_expression(node.right, code)
        code.add_op(TOKEN_TO_BINOP[node.op.content], None)
        return code
    elif isinstance(node, UnaryOp):
        raise ValueError
    elif isinstance(node, Function):
        compile_function(node, code)
        return code
    elif isinstance(node, Call):
        compile_expression(node.callable, code)
        for arg in node.arguments:
            compile_expression(arg, code)
        code.add_op(('CALL_FUNCTION', len(node.arguments)), None)
        return code
    raise ValueError(f"Don't know what this is: {node}")

def compile_statement(stmt, code):
    if isinstance(stmt, (BinaryOp, UnaryOp, Token, Call)):
        code = compile_expression(stmt, code)
        code.add_op('POP_TOP', None)
        return code
    elif isinstance(stmt, Assignment):
        code = compile_expression(stmt.rhs, code)
        assert stmt.lhs.kind == 'Variable', stmt.lhs
        code.add_store_var_op(stmt.lhs.content, stmt.lhs.lineno)
        return code
    elif isinstance(stmt, If):
        compile_expression(stmt.condition, code)
        if stmt.else_body:
            else_label = code.make_label('else')
            code.add_op(('POP_JUMP_IF_FALSE', else_label), None)
            for s in stmt.body:
                compile_statement(s, code)
            end_label = code.make_label('end')
            code.add_op(('JUMP_ABSOLUTE', end_label), None)
            code.set_target(else_label)
            for s in stmt.body:
                compile_statement(s, code)
            code.set_target(end_label)
        else:
            raise ValueError(f"TODO: if without else")
        return code
    elif isinstance(stmt, While):
        raise ValueError(f"don't know how to compile stmt of type {type(stmt)}")
    elif isinstance(stmt, Run):
        raise ValueError(f"don't know how to compile stmt of type {type(stmt)}")
    elif isinstance(stmt, Return):
        raise ValueError(f"don't know how to compile stmt of type {type(stmt)}")
    else:
        raise ValueError(f"don't know how to compile stmt of type {type(stmt)}")

def compile_function(node, code):
    params = [t.content for t in node.params]
    st = code.scope_analyzer[node]
    func_code = MutableCode(symbol_table=st, params=params, scope_analyzer=code.scope_analyzer,
                            filename=code.filename, name=code.name, firstlineno=node.token.lineno)
    for stmt in node.body:
        compile_statement(stmt, func_code)

    # add a return None in case execute reaches here (but other returns are allowed)
    n = func_code.register_const(None)
    func_code.add_op(('LOAD_CONST', n), None)
    func_code.add_op('RETURN_VALUE', None)
    func_code_obj = func_code.to_code_object()

    if func_code.freevars:
        for inner_freevar in func_code.freevars:
            n = code.cellvar_or_freevar_offset(inner_freevar)
            code.add_op(('LOAD_CLOSURE', n), node.token.lineno)
        code.add_op(('BUILD_TUPLE', len(func_code.freevars)), node.token.lineno)

    n = code.register_const(func_code_obj)
    code.add_op(('LOAD_CONST', n), node.token.lineno)
    n = code.register_const(func_code.name)
    code.add_op(('LOAD_CONST', n), node.token.lineno)
    if func_code.freevars:
        code.add_op(('MAKE_FUNCTION', 0x08), node.token.lineno)
    else:
        code.add_op(('MAKE_FUNCTION', 0x00), node.token.lineno)
    return code

def compile_module(stmts, source_filename, name):
    scope_analyzer = ScopeAnalyzer()
    scope_analyzer.discover_symbols(stmts)

    code = MutableCode(scope_analyzer.global_symbol_table, (), scope_analyzer, source_filename, name)
    for stmt in stmts:
        compile_statement(stmt, code)

    # modules always end with an implicit return None
    n = code.register_const(None)
    code.add_op(('LOAD_CONST', n), None)
    code.add_op('RETURN_VALUE', None)
    return code

def calc_ast_to_python_code_object(stmts, source_filename='fakefile.calc', name='calc_code'):
    return compile_module(stmts, source_filename, name).to_code_object()

def calc_ast_to_python_func(stmts):
    codeobj = calc_ast_to_python_code_object(stmts, 'fakefile.calc', 'calc_function')
    PyFunction = type(lambda: None)
    f = PyFunction(codeobj, {'print': print})
    return f

def calc_ast_to_python_module(stmts):
    codeobj = calc_ast_to_python_code_object(stmts, 'fakefile.calc', 'calc_module')
    Module = type(sys)
    module = Module('calc_module', "Doc string for calc module")
    module.__file__ = 'fakefile.calc'
    exec(codeobj, module.__dict__)
    return module

def calc_source_to_python_code_object(s):
    return calc_ast_to_python_code_object(tokenize(parse(s)), 'fakefile.calc', 'calc_code')

def calc_source_to_python_func(s):
    """
    >>> f = calc_source_to_python_func('print(1 + 1);')
    >>> f()
    2
    """
    return calc_ast_to_python_func(parse(tokenize(s)))

def calc_source_to_python_module(s):
    """
    >>> f = calc_source_to_python_func('print(1 + 1);')
    >>> f()
    2
    """
    tokens = tokenize(s)
    stmts = parse(tokens)
    return calc_ast_to_python_module(stmts)

def compile_expression_from_source(source):
    """
    >>> compile_expression_from_source('1')
    MutableCode(opcodes=[
                         ('LOAD_CONST', 0)
                        ],
    constants=[1])
    >>> compile_expression_from_source('1 + 2')
    MutableCode(opcodes=[
                         ('LOAD_CONST', 0),
                         ('LOAD_CONST', 1),
                         'BINARY_ADD'
                        ],
    constants=[1, 2])
    """
    tokens = tokenize(source)
    node, remaining_tokens = parse_expression(tokens)
    assert not remaining_tokens, f'leftover tokens: {remaining_tokens}'
    scope_analyzer = ScopeAnalyzer()
    scope_analyzer.discover_symbols([node])
    code = MutableCode(scope_analyzer.global_symbol_table, (), scope_analyzer)
    return compile_expression(node, code)


if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) > 0:
        filename, = args
        assert filename.endswith('.calc')
        compile_calc_file(args)
    else:
        import doctest
        doctest.testmod()
