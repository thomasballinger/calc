from tokens import Token, tokenize
from parse import BinaryOp, UnaryOp, pprint_tree, parse, Assignment, If, While, Call, Return, Function, Run, PropAccess, Class, Compile, parse_expression
from scope_analysis import ScopeAnalyzer

import sys
import opcode
import os

class MutableCode:
    def __init__(self, symbol_table, params, scope_analyzer, filename=None, name=None, firstlineno=None):
        self.symbol_table = symbol_table
        self.scope_analyzer = scope_analyzer  # used to get nested scopes
        self.opcodes = []  # the compiled code!
        self.linenos = []

        self.constants = []  # All the numbers, strings, booleans we'll need, always including None

        self.names = []  # globals and attribute
        self.freevars = []
        self.cellvars = []
        self.varnames = []

        self.filename = filename or 'fakefilename'
        self.name = name or 'fakename'
        self.firstlineno = firstlineno
        self.last_lineno = None
        self.params = params

        for cellvar in symbol_table.cell_vars:
            self.cellvars.append(cellvar)

        for freevar in symbol_table.free_vars:
            self.freevars.append(freevar)

        for globalvar in symbol_table.global_vars:
            self.names.append(globalvar)

        self.varnames = list(params)
        for local_var in symbol_table.local_vars:
            if local_var not in self.varnames:
                self.varnames.append(local_var)

        #TODO: try implementing if

    def register_const(self, const):
        if const in self.constants:
            return self.constants.index(const)
        self.constants.append(const)
        return len(self.constants) - 1

    def name_offset(self, name):
        return self.names.index(name)

    def cellvar_or_freevar_offset(self, name):
        return (self.cellvars + self.freevars).index(name)

    def cellvar_offset(self, name):
        return self.cellvars.index(name)

    def local_offset(self, name):
        return self.varnames.index(name)

    # LOAD_CLOSURE loads pushes a reference (cellvars + freevars)[i]

    # We can't just register as we go! We need to know the length of cellvars up front.

    def add_load_var_op(self, name, lineno):
        if name in self.symbol_table.global_vars:
            self.add_op(('LOAD_GLOBAL', self.name_offset(name)), lineno)
        elif name in self.symbol_table.cell_vars:
            self.add_op(('LOAD_DEREF', self.cellvar_or_freevar_offset(name)), lineno)
            # LOAD_DEREF loads pushes a reference (cellvars + freevars)[i]
        elif name in self.symbol_table.free_vars:
            self.add_op(('LOAD_DEREF', self.cellvar_or_freevar_offset(name)), lineno)
        elif name in self.symbol_table.local_vars:
            self.add_op(('LOAD_FAST', self.local_offset(name)), lineno)

    def add_store_var_op(self, name, lineno):
        if name in self.symbol_table.global_vars:
            self.add_op(('STORE_GLOBAL', self.name_offset(name)), lineno)
        elif name in self.symbol_table.cell_vars:
            self.add_op(('STORE_DEREF', self.cellvar_or_freevar_offset(name)), lineno)
        elif name in self.symbol_table.free_vars:
            self.add_op(('STORE_DEREF', self.cellvar_or_freevar_offset(name)), lineno)
        elif name in self.symbol_table.local_vars:
            self.add_op(('STORE_FAST', self.local_offset(name)), lineno)

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

        # names = []  # global variables or attribute calls
        # varnames: parameters, then local variable names (except cellvars!)
        # freevars: references to outer scopes
        # cellvars: local variables referenced by inner scopes

        codestring = opcode_strings_to_codestring(self.opcodes)
        firstlineno, lnotab = self.build_firstlineno_lnotab()
        codeobj = module_code_to_pyc_contents(
            argcount=len(self.params),
            nlocals=len(self.varnames),
            codestring=codestring,
            constants=tuple(self.constants),
            names=tuple(self.names),
            varnames=tuple(self.varnames),
            firstlineno=firstlineno,
            lnotab=lnotab,
            freevars=tuple(self.freevars),
            cellvars=tuple(self.cellvars),
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
        raise ValueError(f"don't know how to compile stmt of type {type(stmt)}")
    elif isinstance(stmt, While):
        raise ValueError(f"don't know how to compile stmt of type {type(stmt)}")
    elif isinstance(stmt, Run):
        raise ValueError(f"don't know how to compile stmt of type {type(stmt)}")
    elif isinstance(stmt, Return):
        raise ValueError(f"don't know how to compile stmt of type {type(stmt)}")
    else:
        raise ValueError(f"don't know how to compile stmt of type {type(stmt)}")

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

def module_code_to_pyc_contents(argcount, nlocals, codestring, constants, names, varnames, firstlineno, lnotab, freevars, cellvars, filename, name):
    """
    codestring: the compiled code!
    names: global variables or attribute calls
    constants: All the numbers, strings, booleans we'll need, always including None
    varnames: parameters, then local variables
    filename: source code filename
    name: function or module name
    """
    kwonlyargcount = 0  # calc functions have no kwarg-only args
    nlocals = 0  # modules just have global variables, no locals
    freevars = ()  #  (none for modules)
    callvars = ()  # local variables referenced by nested functions (none for modules)
    fake_stacksize = 100

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
    c = code(argcount, kwonlyargcount, nlocals, fake_stacksize, flags, codestring,
          constants, names, varnames, filename, name, firstlineno, lnotab, freevars, cellvars)
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
