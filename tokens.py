from collections import namedtuple

class Token(namedtuple('Token', ['kind', 'content', 'start', 'end'])):
    @staticmethod
    def from_string(s, start=0):
        """
        >>> Token.from_string('*')
        Token(kind='Star')
        >>> Token.from_string('123')
        Token(kind='Number', content=123)
        """
        end = start + len(s)
        if s == '+': return Token('Plus', s, start, end)
        elif s == '-': return Token('Minus', s, start, end)
        elif s == '*': return Token('Star', s, start, end)
        elif s == '/': return Token('Slash', s, start, end)
        elif s == '(': return Token('Left Paren', s, start, end)
        elif s == ')': return Token('Right Paren', s, start, end)
        elif s == '>': return Token('Greater', s, start, end)
        elif s == '=': return Token('Equals', s, start, end)
        elif s == '<': return Token('Less', s, start, end)
        elif s == 'p': return Token('Print', s, start, end)
        elif s == 's': return Token('String', s, start, end)
        elif s == 'l': return Token('Length', s, start, end)
        elif s in ('x', 'y', 'z'): return Token('Variable', s, start, end)
        elif s == ';': return Token('Semi', s, start, end)
        elif s.isnumeric(): return Token('Number', int(s), start, end)
        else: raise ValueError("Can't parse string '{}' into token".format(s))
    
    """
    def __repr__(self):
        if self.kind in ("Number", "Variable"):
            return f"Token(kind={self.kind}, content={self.content})"
        return f"Token(kind={self.kind})"
    """

def tokenize(string):
    """
    >>> tokenize('1 - 22')
    [Token(kind='Number', content=1), Token(kind='Minus', content='-'), Token(kind='Number', content=22)]
    """
    tokens = []
    token_string = ''
    for i, c in enumerate(string):
        if c in (' ', '\n'):
            if token_string:
                tokens.append(Token.from_string(token_string, i-len(token_string)))
                token_string = ''
            token_string = ''
        elif c in ('+', '-', '*', '/', '(', ')', '>', '<', '=', 'p', 's', 'l', 'x', 'y', 'z', ';'):
            working_on_a_number = False
            if token_string:
                tokens.append(Token.from_string(token_string, i-len(token_string)))
                token_string = ''
            tokens.append(Token.from_string(c, i))
        elif c.isnumeric():
            token_string += c
        else:
            raise ValueError('Unknown character: {}'.format(c))

    if token_string:
        tokens.append(Token.from_string(token_string, i-len(token_string)))

    return tokens
