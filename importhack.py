import sys
import opcode
import importlib
import os

from compile import calc_ast_to_python_code_object
from parse import parse
from tokens import tokenize

class CalcImporter(object):
    def __init__(self):
        pass

    def find_module(self, fullname, path=None):
        if (fullname + '.calc') in os.listdir('.'):
            # let's compile it right now!
            source = open(fullname + '.calc').read()
            print('bytecode-compiling ' + fullname + '.calc...')
            data = calc_code_to_pyc_contents(source, fullname + '.calc')
            with open(fullname + '.pyc', 'wb') as f:
                f.write(data)
            return None
        return None

code_to_pyc = None
import importlib
if hasattr(importlib._bootstrap_external, '_code_to_timestamp_pyc'):
    code_to_pyc = importlib._bootstrap_external._code_to_timestamp_pyc
elif hasattr(importlib._bootstrap_external, '_code_to_bytecode'):
    code_to_pyc = importlib._bootstrap_external._code_to_bytecode

# just for testing
def python_code_to_pyc_contents(source, filename):
    code = compile(source, filename, 'exec')
    return code_to_pyc(code, mtime=0, source_size=0)

def calc_code_to_pyc_contents(source, filename):
    tokens = tokenize(source)
    statements = parse(tokens)
    code = calc_ast_to_python_code_object(statements, filename)
    return code_to_pyc(code, mtime=0, source_size=0)

def shim():
    # remove any previously-added CalcImporter (to avoid multiple print messages)
    sys.meta_path = [loader for loader in sys.meta_path
                     if str(type(loader)) != str(type(CalcImporter()))]
    sys.meta_path.insert(0, CalcImporter())


if __name__ == '__main__':
    import doctest
    doctest.testmod()
