from tokens import Token, tokenize
from parse import BinaryOp, UnaryOp, pprint_tree, parse, Assignment, If, While, Call, Return, Function, Run, PropAccess, Class, Compile, parse_expression
import subprocess
import os

class MipsAsm:
    def __init__(self, source_lines):
        self.text_lines = []
        self.data_lines = []
        # no spilling strategy, allocation, use each once lol
        self.unused_variable_registers = [
            '$s7', '$s6', '$s5', '$s4', '$s3', '$s2', '$s1', '$s0', 
        ]
        # no spilling strategy, so only 8 temp regs allowed
        self.unused_tmp_registers = [
            '$t7', '$t6', '$t5', '$t4', '$t3', '$t2', '$t1', '$t0', 
        ]
        self.psuedostack = []  # temp regs in use
        self.stored_variables = {}
        self.last_const_suffix = -1
        self.last_source_lineno = 0
        self.source_lines = source_lines

    def push_to_temp(self):
        reg = self.unused_tmp_registers.pop()
        self.psuedostack.append(reg)
        return reg

    def pop_from_temp(self):
        reg = self.psuedostack.pop()
        self.unused_tmp_registers.append(reg)
        return reg

    def add_line(self, line, lineno):
        if lineno is not None and lineno > self.last_source_lineno:
            lines = self.source_lines[self.last_source_lineno:lineno]
            for source_line in lines:
                if source_line.strip():
                    self.text_lines.append('')
                    self.text_lines.append(f'# {source_line}')
            self.last_source_lineno = lineno
        self.text_lines.append(line)

    def add_store_var_op(self, varname, lineno):
        if varname in self.stored_variables:
            reg = self.stored_variables[varname]
        else:
            reg = self.unused_variable_registers.pop()
            self.stored_variables[varname] = reg

        self.add_line(f'move {reg}, {self.pop_from_temp()}', lineno)

    def add_load_var_op(self, varname, lineno):
        reg = self.stored_variables[varname]
        self.add_line(f'move {self.push_to_temp()}, {reg}', lineno)

    def register_const(self, value, name=None):
        self.last_const_suffix += 1
        if name is None:
            name = f'const_{self.last_const_suffix}'
        else:
            name = f'const_{name}_{self.last_const_suffix}'
        if isinstance(value, int):
            self.data_lines.append(
                f'{name}: .word {value}'
            )
        else:
            raise ValueError()
        return name


    def generate(self):
        nl = '\n'
        return f""".data
{nl.join(' '*4 + line for line in self.data_lines)}

.text
.globl main

main:
{nl.join(' '*4 + line for line in self.text_lines)}"""

TOKEN_TO_BINOP = {
    '+': 'add',
    '-': 'sub',
}

def compile_expression(node, code, name_if_constant=None):
    if isinstance(node, Token):
        if node.kind == 'Number':
            constant_name = code.register_const(node.content, name_if_constant)
            code.add_line(f'lw {code.push_to_temp()}, {constant_name}', node.lineno)
            return code
        elif node.kind == 'Variable':
            # lookup
            code.add_load_var_op(node.content, node.lineno)
            return code
        elif node.kind == 'String':
            raise ValueError("can't make string constants yet");

    elif isinstance(node, BinaryOp):
        compile_expression(node.left, code)
        compile_expression(node.right, code)
        opcode = TOKEN_TO_BINOP[node.op.content]
        left_reg = code.pop_from_temp()
        right_reg = code.pop_from_temp()
        dest_reg = code.push_to_temp()
        code.add_line(f'{opcode} {dest_reg}, {left_reg}, {right_reg}', node.op.lineno)
        return code
    elif isinstance(node, UnaryOp):
        raise ValueError("can't compile unaryop")
    elif isinstance(node, Function):
        raise ValueError("can't compile function definition")
    elif isinstance(node, Call):
        # hardcoding print int as only implemented function
        assert(len(node.arguments) == 1)
        assert(node.callable.content == 'print')

        for arg in node.arguments:
            compile_expression(arg, code)
        code.add_line(f'move $a0, {code.pop_from_temp()}', node.callable.lineno)
        code.add_line(f'li $v0, 1', None)
        code.add_line('syscall', None)

        # fake return value for print() with junk
        code.push_to_temp()

        return code
    raise ValueError(f"Don't know what this is: {node}")

def compile_statement(stmt, code):
    if isinstance(stmt, (BinaryOp, UnaryOp, Token, Call)):
        code = compile_expression(stmt, code)
        code.pop_from_temp()
        return code
    elif isinstance(stmt, Assignment):
        code = compile_expression(stmt.rhs, code, stmt.lhs.content)
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

def compile_module(stmts, source_lines):
    code = MipsAsm(source_lines)
    for stmt in stmts:
        compile_statement(stmt, code)

    # modules always end with a halt
    code.add_line('li $v0, 10', None)
    code.add_line('syscall', None)
    return code

def generate_asm(s):
    if '\n' not in s and os.path.exists(s):
        s = open(s).read()
    tokens = tokenize(s)
    stmts = parse(tokens)
    module = compile_module(stmts, s.splitlines())
    mips_source = module.generate()
    return mips_source

def run_as_mips(s):
    mips_asm = generate_asm(s)
    print(mips_asm)
    run(mips_asm)

def run(s):
    f = open('tmp.asm', 'wb')
    f.write(s.encode('utf-8'))
    f.flush()
    result = subprocess.run(['spim', '-file', f.name],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    output = '\n'.join(
        ([result.stdout.decode('utf-8')] if result.stdout else []) +
        ([result.stderr.decode('utf-8')] if result.stderr else [])
    )
    lines = output.splitlines()
    print('\n'.join(line for line in lines
                    if not line.startswith('Loaded:')))

def test():
    """
    >>> print(generate_asm('''
    ... a = 1 + 2;
    ... b = 2 - 3;
    ... print(a + b);
    ... '''))
    .data
        const_0: .word 1
        const_1: .word 2
        const_2: .word 2
        const_3: .word 3
    <BLANKLINE>
    .text
    .globl main
    <BLANKLINE>
    main:
    <BLANKLINE>
        # a = 1 + 2;
        lw $t0, const_0
        lw $t1, const_1
        add $t0, $t1, $t0
        move $s0, $t0
    <BLANKLINE>
        # b = 2 - 3;
        lw $t0, const_2
        lw $t1, const_3
        sub $t0, $t1, $t0
        move $s1, $t0
    <BLANKLINE>
        # print(a + b);
        move $t0, $s0
        move $t1, $s1
        add $t0, $t1, $t0
        move $a0, $t0
        li $v0, 1
        syscall
        li $v0, 10
        syscall
    """

if __name__ == '__main__':
    import doctest
    doctest.testmod()

