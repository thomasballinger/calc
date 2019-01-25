import opcode

class MutableCode:
    def __init__(self, symbol_table, params, scope_analyzer, filename=None, name=None, firstlineno=None):
        self.symbol_table = symbol_table
        self.scope_analyzer = scope_analyzer  # used to get nested scopes
        self.opcodes = []  # the compiled code!
        self.linenos = []
        self.labels = {}

        self.constants = []  # All the numbers, strings, booleans we'll need, always including None
        self.names = []  # globals and attribute
        self.freevars = []  # variables we were passed closure cells for
        self.cellvars = []  # variables we created our own closure cells for
        self.varnames = []  # parameters, then local variables

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

    def make_label(self, comment='?'):
        label = f'label-{len(self.labels)}-{comment}'
        self.labels[label] = None
        return label

    def set_target(self, label):
        """Sets a label to the point to the next bytecode"""
        self.labels[label] = len(self.opcodes)

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

    def resolve_labels(self):
        for i in range(len(self.opcodes)):
            if len(self.opcodes[i]) == 2 and isinstance(self.opcodes[i][1], str):
                label = self.opcodes[i][1]
                assert label.startswith('label'), f"bad label name: {self.opcodes[i]}"
                value = self.labels[label] * 2  # for two bytes per opcode
                #print('resolving label', self.opcodes[i][1], 'to', value)
                self.opcodes[i] = (self.opcodes[i][0], value)

    def to_code_object(self):

        # names = []  # global variables or attribute calls
        # varnames: parameters, then local variable names (except cellvars!)
        # freevars: references to outer scopes
        # cellvars: local variables referenced by inner scopes

        self.resolve_labels()
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

