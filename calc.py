import sys as _sys

from debugrepl import debug_repl
from compile import calc_source_to_python_func
from importhack import shim as _shim

if __name__ == '__main__':
    args = _sys.argv[1:]
    if len(args) == 1:
        run_program(open(args[0]).read())
    else:
        debug_repl()

else:
    # when this module is imported, run the import shim as a side effect
    _shim()
