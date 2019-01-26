import unittest
import sys
from textwrap import dedent

from calc import calc_source_to_python_module, calc_source_to_python_code_object
from parse import parse
from tokens import tokenize
from scope_analysis import ScopeAnalyzer
from contextlib import contextmanager
from io import StringIO

@contextmanager
def CapturedOutput():
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err

def python_module(source):
    Module = type(unittest)
    module = Module('python_module', "Doc string for python module")
    module.__file__ = 'fakefile.py'
    exec(source, module.__dict__)
    return module

class TestCompile(unittest.TestCase):

    def test_compile_tool(self):
        calc_source_to_python_code_object('a = 1; b = "hello";')

    def test_simpler(self):
        calcmod = calc_source_to_python_module(dedent("""
            a = 1;
            """))

    def test_simple(self):
        calcmod = calc_source_to_python_module(dedent("""
            a = 1;
            foo = (a, b) =>
              print(c);
            end;"""))

class TestCompiledPythonOutputMatches(unittest.TestCase):

    def test_simple(self):
        with CapturedOutput() as (calc_out, _):
            calcmod = calc_source_to_python_module(dedent("""
                a = 1;
                c = 2;
                foo = (a, b) =>
                  print(c);
                  print(a);
                  bar = (d) =>
                    print(a);
                    print(e);
                  end;
                end;"""))
            calcmod.foo(1, 2)

        with CapturedOutput() as (py_out, _):
            pymod = python_module(dedent("""
                a = 1;
                c = 2;
                def foo(a, b):
                    print(c)
                    print(a);
                    def bar(d):
                        print(a)
                        print(e)
                """))
            pymod.foo(1, 2)

        self.assertEqual(calc_out.getvalue(), py_out.getvalue())


class TestScopeAnalysis(unittest.TestCase):

    def test_top_level_locals_are_globals(self):
        ast = parse(tokenize("""
            a = 1;
        """))

        sa = ScopeAnalyzer()
        sa.discover_symbols(ast)

        self.assertEqual(sa.global_symbol_table.global_vars, {'a'})

    def test_simple(self):
        ast = parse(tokenize("""
            a = 1;
            foo = (a, b) =>
              print(c);
              bar = (d) =>
                print(a);
                print(e);
              end;
              if a < 12 then
                e = 17;
              end;
            end;"""))

        sa = ScopeAnalyzer()
        sa.discover_symbols(ast)

        sa.global_symbol_table
        foo = sa[ast[1].rhs]

        self.assertEqual(foo.local_vars, {'b', 'bar'})
        self.assertEqual(foo.global_vars, {'c', 'print'})
        self.assertEqual(foo.cell_vars, {'a', 'e'})
        self.assertEqual(foo.free_vars, dict())

    def test_passthrough_freevars(self):
        ast = parse(tokenize("""
            notglobal = () =>
              a = 1;
              b = 2;
              foo = () =>
                fooinner = () =>
                  print(a);
                end;
              end;
              bar = () =>
                barinner = () =>
                  print(b);
                end;
              end;
            end;"""))

        sa = ScopeAnalyzer()
        sa.discover_symbols(ast)

        sa.global_symbol_table
        not_global = sa[ast[0].rhs]
        foo = sa[ast[0].rhs.body[2].rhs]
        bar = sa[ast[0].rhs.body[3].rhs]

        self.assertEqual(not_global.cell_vars, {'a', 'b'})

        self.assertEqual(foo.free_vars, {'a': not_global})
        self.assertEqual(bar.free_vars, {'b': not_global})


if __name__ == '__main__':
    unittest.main()
