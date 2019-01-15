from collections import namedtuple

class Token(namedtuple('Token', ['kind', 'content'])):
    @staticmethod
    def from_string(s):
        """
        >>> Token.from_string('*')
        Token(kind='Star', content='*')
        >>> Token.from_string('123')
        Token(kind='Number', content=123)
        """
        if s == '+': return Token('Plus', s)
        elif s == '-': return Token('Minus', s)
        elif s == '*': return Token('Star', s)
        elif s == '/': return Token('Slash', s)
        elif s == '(': return Token('Left Paren', s)
        elif s == ')': return Token('Right Paren', s)
        elif s == '>': return Token('Greater', s)
        elif s == '=': return Token('Equals', s)
        elif s == '<': return Token('Less', s)
        elif s == 'p': return Token('Print', s)
        elif s == 's': return Token('String', s)
        elif s == 'l': return Token('Length', s)
        elif s in ('x', 'y', 'z'): return Token('Variable', s)
        elif s.isnumeric(): return Token('Number', int(s))
        else: raise ValueError("Can't parse string '{}' into token".format(s))

def tokenize(string):
    """
    >>> tokenize('1 - 22')
    [Token(kind='Number', content=1), Token(kind='Minus', content='-'), Token(kind='Number', content=22)]
    """
    tokens = []
    token_string = ''
    for c in string:
        if c == ' ':
            if token_string:
                tokens.append(Token.from_string(token_string))
                token_string = ''
            token_string = ''
        elif c in ('+', '-', '*', '/', '(', ')', '>', '<', '=', 'p', 's', 'l', 'x', 'y', 'z'):
            working_on_a_number = False
            if token_string:
                tokens.append(Token.from_string(token_string))
                token_string = ''
            tokens.append(Token.from_string(c))
        elif c.isnumeric():
            token_string += c

    if token_string:
        tokens.append(Token.from_string(token_string))

    return tokens

