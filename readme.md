# Calc

A calculator stretched into a language

Try it out on replit: https://repl.it/@thomasballinger2/compilecalctopython

I taught a compilers/languages course at Bradfield where we used a lot of http://craftinginterpreters.com/, but some people fell off the aggressive schedule of implementing the language in that book, Lox. In order to bring along folks who couldn't keep up we worked together on this calculator in Python.

This project was optimized for live coding / mob programming in class, so choices like "strings instead of enums" that assist with fitting code on a screen but make the code less maintainable abound.

At various points in the commit history, this project has:
* a tokenizer
* a parser
* a tree-walk interpreter
* a type-checker
* a Python 3.6/7 bytecode compiler
* interop with Python!

but these things don't necessarily all work together ;)

copyright Bradfield School of Computer Science
