from tokens import Token, tokenize
from parse import BinaryOp, UnaryOp, pprint_tree, parse, Assignment, If, While, Call, Return, Function, Run, PropAccess, Class, Compile, parse_expression

import sys
import opcode
import os

class Code:
    def __init__(self):
        self.opcodes = []  # the compiled code!
        self.stacksize = 100  # max anticipated size of the value stack
        self.names = []  # global variables or attribute calls
        self.constants = []  # All the numbers, strings, booleans we'll need, always including None

    def register_name(self, name):
        if name in self.names:
            return self.names.index(name)
        self.names.append(name)
        return len(self.names) - 1

    def register_constant(self, const):
        if const in self.constants:
            return self.constants.index(const)
        self.constants.append(const)
        return len(self.constants) - 1

    def add_op(self, op, arg=None):
        if op not in opcode.opmap:
            raise ValueError(f"Unknown Op: {op}")
        if opcode.opmap[op] > opcode.HAVE_ARGUMENT:
            if arg is None:
                raise ValueError(f"Opcode {op} needs argument")
        else:
            if arg is not None:
                raise ValueError(f"Opcode {op} does not take an argument")

        self.opcodes.append(op if arg is None else (op, arg))

    def __repr__(self):
        nl = '\n'
        opcodespace = len('Code(opcodes=[') * ' '
        closebracketspace = (len('Code(opcodes=[') - 1) * ' '
        argspace = len('Code(') * ' '
        instructions = f',\n{opcodespace}'.join(f"{repr(both)}"
                                                for both in self.opcodes)
        s = f"Code(opcodes=[{nl}{opcodespace}{instructions}{nl}{closebracketspace}]"
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

def compile_expression(node, code=None):
    """
    >>> compile_expression(parse_expression(tokenize('1'))[0])
    Code(opcodes=[
                  ('LOAD_CONST', 0)
                 ],
    constants=[1])
    >>> compile_expression(parse_expression(tokenize('1 + 2'))[0])
    Code(opcodes=[
                  ('LOAD_CONST', 0),
                  ('LOAD_CONST', 1),
                  'BINARY_ADD'
                 ],
    constants=[1, 2])
    """
    if code is None: code = Code()
    if isinstance(node, Token):
        if node.kind == 'Number':
            n = code.register_constant(node.content)
            code.add_op('LOAD_CONST', n)
            return code
        elif node.kind == 'Variable':
            raise ValueError("Can't compile variable access")
        elif node.kind == 'String':
            return node.content

    elif isinstance(node, BinaryOp):
        compile_expression(node.left, code)
        compile_expression(node.right, code)
        code.add_op(TOKEN_TO_BINOP[node.op.content])
        return code
    elif isinstance(node, UnaryOp):
        raise ValueError
    raise ValueError(f"Don't know what this is: {node}")


def compile_statement(stmt, code=None):
    if code is None: code = Code()
    if isinstance(stmt, (BinaryOp, UnaryOp, Token, Call)):
        code = compile_expression(stmt)
        code.add_op('POP_TOP')
        return code
    else:
        raise ValueError("don't know how to compile stmt of type {type(stmt)}")

def compile_module(stmts):
    code = Code()
    for stmt in stmts:
        compile_statement(stmt)


"""
    code(argcount, kwonlyargcount, nlocals, stacksize, flags, codestring,
          constants, names, varnames, filename, name, firstlineno,
          lnotab[, freevars[, cellvars]])

    Create a code object.  Not for the faint of heart.
"""

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
        codestring += (chr(n).encode() + chr(arg).encode())
    return codestring


def calc_module_code_to_pyc_contents(codestring, stacksize, names, constants, filename):
    """
    codestring: the compiled code!
    stacksize: max anticipated size of the value stack
    names: global variables or attribute calls
    constants: # All the numbers, strings, booleans we'll need, always including None
    """
    argcount = 0  # modules have no args
    kwonlyargcount = 0  # modules have no args
    nlocals = 0  # modules just have global variables, no locals
    varnames = ()  # paremeters, then local variables
    freevars = ()  #  (none for modules)
    callvars = ()  # local variables referenced by nested functions (none for modules)
    fake_name = 'madeup'
    fake_firstlineno = 1

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

    fake_lnotab = b'\x00\x01' + (b'\x01\x01' * ((len(codestring) - 1)))

    code = type((lambda: None).__code__)
    c = code(argcount, kwonlyargcount, nlocals, stacksize, flags, codestring,
          constants, names, varnames, filename, fake_name, fake_firstlineno, fake_lnotab)
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
