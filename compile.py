from tokens import Token, tokenize
from parse import BinaryOp, UnaryOp, pprint_tree, parse, Assignment, If, While, Call, Return, Function, Run, PropAccess, Class, Compile, parse_expression

import sys
import opcode
import os

class MutableCode:
    def __init__(self, filename=None, name=None, firstlineno=None):
        self.opcodes = []  # the compiled code!
        self.linenos = []  # the compiled code!
        self.stacksize = 100  # max anticipated size of the value stack
        self.names = []  # global variables or attribute calls
        self.constants = []  # All the numbers, strings, booleans we'll need, always including None
        self.filename = filename or 'fakefilename'
        self.name = name or 'fakename'
        self.firstlineno = firstlineno
        self.last_lineno = None

    def register_name(self, name):
        if name in self.names:
            return self.names.index(name)
        self.names.append(name)
        return len(self.names) - 1

    def register_const(self, const):
        if const in self.constants:
            return self.constants.index(const)
        self.constants.append(const)
        return len(self.constants) - 1

    def set_lineno(self, lineno):
        self.last_lineno = lineno

    def add_op(self, op_and_arg, lineno):
        if len(op_and_arg) == 2:
            op, arg = op_and_arg
        else:
            op, arg = op_and_arg, None

        if op not in opcode.opmap:
            raise ValueError(f"Unknown Op: {op}")
        if opcode.opmap[op] >= opcode.HAVE_ARGUMENT:
            if arg is None:
                raise ValueError(f"Opcode {op} needs argument")
        else:
            if arg is not None:
                raise ValueError(f"Opcode {op} does not take an argument")

        if lineno is None:
            lineno = self.last_lineno or 1
        self.last_lineno = lineno

        self.opcodes.append(op if arg is None else (op, arg))
        self.linenos.append(lineno)

    def build_firstlineno_lnotab(self):
        if self.firstlineno is None:
            firstlineno = self.linenos[0]
        else:
            firstlineno = self.firstlineno
        last_bytecode_index = 0
        last_lineno = 0
        offsets = [last_bytecode_index, last_lineno]
        for opno, abs_lineno in enumerate(self.linenos):
            lineno = abs_lineno - firstlineno
            bytecode_index = opno * 2
            if lineno > last_lineno:
                offsets.append(bytecode_index - last_bytecode_index)
                last_bytecode_index = bytecode_index
                offsets.append(lineno - last_lineno)
                last_lineno = lineno
        return firstlineno, bytes(offsets)

    def to_code_object(self):
        codestring = opcode_strings_to_codestring(self.opcodes)
        firstlineno, lnotab = self.build_firstlineno_lnotab()
        codeobj = module_code_to_pyc_contents(
            codestring=codestring,
            stacksize=100,
            names=tuple(self.names),
            constants=tuple(self.constants),
            firstlineno=firstlineno,
            lnotab=lnotab,
            filename=self.filename,
            name=self.name,
        )
        return codeobj

    def __repr__(self):
        nl = '\n'
        opcodespace = len('MutableCode(opcodes=[') * ' '
        closebracketspace = (len('MutableCode(opcodes=[') - 1) * ' '
        argspace = len('MutableCode(') * ' '
        instructions = f',\n{opcodespace}'.join(f"{repr(both)}"
                                                for both in self.opcodes)
        s = f"MutableCode(opcodes=[{nl}{opcodespace}{instructions}{nl}{closebracketspace}]"
        if self.constants:
            s += f",{nl}constants={self.constants}"
        s += ')'
        return s

TOKEN_TO_BINOP = {
    '*': 'BINARY_MULTIPLY',
    '%': 'BINARY_MODULO',
    '+': 'BINARY_ADD',
    '-': 'BINARY_SUBTRACT',
    '/': 'BINARY_TRUE_DIVIDE',
}

def compile_expression_from_source(source):
    """
    >>> compile_expression_from_source'1')
    MutableCode(opcodes=[
                         ('LOAD_CONST', 0)
                        ],
    constants=[1])
    >>> compile_expression_from_source'1 + 2')
    MutableCode(opcodes=[
                         ('LOAD_CONST', 0),
                         ('LOAD_CONST', 1),
                         'BINARY_ADD'
                        ],
    constants=[1, 2])
    """
    tokens = tokenize(source)
    node, remaining_tokens = parse_expression(tokens)[0]
    assert not remaining_tokens, f'leftover tokens: {remaining_tokens}'
    code = MutableCode()
    return compile_expression(node, code)

def compile_expression(node, code):
    if isinstance(node, Token):
        if node.kind == 'Number':
            n = code.register_const(node.content)
            code.add_op(('LOAD_CONST', n), node.lineno)
            return code
        elif node.kind == 'Variable':
            # TODO add semantic analysis phase because Variable isn't specific enough
            # global variable
            n = code.register_name(node.content)
            code.add_op(('LOAD_GLOBAL', n), node.lineno)
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
        n = code.register_name(stmt.lhs.content)
        code.add_op(('STORE_NAME', n), stmt.lhs.lineno)
        return code
    elif isinstance(stmt, If):
        raise ValueError("don't know how to compile stmt of type {type(stmt)}")
    elif isinstance(stmt, While):
        raise ValueError("don't know how to compile stmt of type {type(stmt)}")
    elif isinstance(stmt, Run):
        raise ValueError("don't know how to compile stmt of type {type(stmt)}")
    elif isinstance(stmt, Return):
        raise ValueError("don't know how to compile stmt of type {type(stmt)}")
    else:
        raise ValueError("don't know how to compile stmt of type {type(stmt)}")

def compile_module(stmts, source_filename, name):
    code = MutableCode(source_filename, name)
    for stmt in stmts:
        compile_statement(stmt, code)

    # modules always end with an implicit return None
    n = code.register_const(None)
    code.add_op(('LOAD_CONST', n), None)
    code.add_op('RETURN_VALUE', None)
    return code

def compile_function(node, code):
    node.params
    func_code = MutableCode(filename=code.filename, name=code.name, firstlineno=node.token.lineno)
    for stmt in node.body:
        compile_statement(stmt, func_code)

    # add a return None in case execute reaches here (but other returns are allowed)
    n = func_code.register_const(None)
    func_code.add_op(('LOAD_CONST', n), None)
    func_code.add_op('RETURN_VALUE', None)
    func_code_obj = func_code.to_code_object()
    n = code.register_const(func_code_obj)
    code.add_op(('LOAD_CONST', n), None)
    n = code.register_const(func_code.name)
    code.add_op(('LOAD_CONST', n), None)
    code.add_op(('MAKE_FUNCTION', 0), None)  # arg is number of default parameters, always 0 for calc
    return code

def calc_ast_to_python_code_object(stmts, source_filename='fakefile', name='calc_code'):
    return compile_module(stmts, source_filename, name).to_code_object()

def calc_ast_to_python_func(stmts):
    codeobj = calc_ast_to_python_code_object(stmts, 'fakefile', 'calc_function')
    PyFunction = type(lambda: None)
    f = PyFunction(codeobj, {'print': print})
    return f

def calc_source_to_python_code_object(s):
    tokens = tokenize(s)
    stmts = parse(tokens)
    codeobj = calc_ast_to_python_code_object(stmts, 'fakefile', 'calc_code')

def calc_source_to_python_func(s):
    """
    >>> f = calc_source_to_python_func('print(1 + 1);')
    >>> f()
    2
    """
    tokens = tokenize(s)
    stmts = parse(tokens)
    return calc_ast_to_python_func(stmts)

def opcode_strings_to_codestring(opcodes):
    r"""
    Given a list of opcodes as strings, or tuples of opcodes and args, return codestring.

    >>> opcode_strings_to_codestring([('LOAD_FAST', 0), 'RETURN_VALUE'])
    b'|\x00S\x00'
    """
    codestring = b''
    for op_or_op_and_arg in opcodes:
        if len(op_or_op_and_arg) == 2:
            op, arg = op_or_op_and_arg
        else:
            op = op_or_op_and_arg
            arg = 0
            n = opcode.opmap[op]
            if n > opcode.HAVE_ARGUMENT:
                raise ValueError(f"Opcode {op} needs argument")
        n = opcode.opmap[op]
        codestring += bytes([n, arg])
    return codestring


def module_code_to_pyc_contents(codestring, stacksize, names, constants, firstlineno, lnotab, filename, name):
    """
    codestring: the compiled code!
    stacksize: max anticipated size of the value stack
    names: global variables or attribute calls
    constants: All the numbers, strings, booleans we'll need, always including None
    filename: source code filename
    name: function or module name
    """
    argcount = 0  # modules have no args
    kwonlyargcount = 0  # modules have no args
    nlocals = 0  # modules just have global variables, no locals
    varnames = ()  # paremeters, then local variables
    freevars = ()  #  (none for modules)
    callvars = ()  # local variables referenced by nested functions (none for modules)

    OPTIMIZED = NEWLOCALS = VARARGS = VARKEYWORDS = NESTED = GENERATOR = NOFREE = COROUTINE = ITERABLE_COROUTINE = False

    flags = sum([
          1 if OPTIMIZED else 0,
          2 if NEWLOCALS else 0,
          4 if VARARGS else 0,
          8 if VARKEYWORDS else 0,
         16 if NESTED else 0,
         32 if GENERATOR else 0,
         64 if NOFREE else 0,
        128 if COROUTINE else 0,
        256 if ITERABLE_COROUTINE else 0,
    ])

    code = type((lambda: None).__code__)
    c = code(argcount, kwonlyargcount, nlocals, stacksize, flags, codestring,
          constants, names, varnames, filename, name, firstlineno, lnotab)
    return c

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) > 0:
        filename, = args
        assert filename.endswith('.calc')
        compile_calc_file(args)
    else:
        import doctest
        doctest.testmod()
