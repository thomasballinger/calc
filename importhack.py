import sys
import opcode
import importlib
import os

from compile import calc_ast_to_python_code_object
from parse import parse
from tokens import tokenize

#TODO make these modules work correctly with bpython's auto-reloading?

class CalcImporter(object):
    def __init__(self):
        pass

    def find_module(self, fullname, path=None):
        if fullname == 'importhack_example':
            print('bytecode-compiling', fullname + '.calc as "a = 1; b = 2"...')
            data = python_code_to_pyc_contents('a = 1; b = 2', fullname + '.calc')
            with open(fullname + '.pyc', 'wb') as f:
                f.write(data)
        elif (fullname + '.calc') in os.listdir('.'):
            print('bytecode-compiling', fullname + '.calc...')
            source = open(fullname + '.calc').read()
            data = calc_code_to_pyc_contents(source, fullname + '.calc')
            with open(fullname + '.pyc', 'wb') as f:
                f.write(data)

            # let's compile it right now!
            # then convince Python to load from compiled
            return None
        return None

def python_code_to_pyc_contents(source, filename):
    code = compile(source, filename, 'exec')
    return importlib._bootstrap_external._code_to_timestamp_pyc(code, mtime=0, source_size=0)

def calc_code_to_pyc_contents(source, filename):
    tokens = tokenize(source)
    statements = parse(tokens)
    code = calc_ast_to_python_code_object(statements, filename)
    return importlib._bootstrap_external._code_to_timestamp_pyc(code, mtime=0, source_size=0)

def shim():
    sys.meta_path.insert(0, CalcImporter())


if __name__ == '__main__':
    import doctest
    doctest.testmod()

else:
    # when this module is imported, run the shim as a side effect
    shim()
