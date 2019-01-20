import glob
words = ['if', 'then', 'else', 'while', 'do', 'run', 'return', 'end;']

def completer(text, state):
   modules = [filename[:-5] for filename in glob.glob('*.calc')]
   candidates = words + modules
   return [word for word in candidates
           if word.startswith(text)][state]
