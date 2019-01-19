from main import debug_exec, tokenize, Scope, builtin_funcs

variables = Scope()
for name in builtin_funcs:
    variables.set(name, builtin_funcs[name])
debug_exec(tokenize("""
a = 0;
b = ()=>
  c = 7;
  a = ()=> print(c); end;
end;
b();
a();
"""), variables)
