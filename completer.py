
words = ['if', 'then', 'else', 'return', 'end;']

def completer(text, state):
   return [word for word in words
           if word.startswith(text)][state]
