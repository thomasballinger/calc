import dis
import calc
import simple

codeobj = calc.calc_source_to_python_code_object("""
a = 1;
b = 2;
print(b);
""")
dis.dis(codeobj)

import simple

import pudb
pudb.set_trace()
a = 10
simple.foo()
b = 20
