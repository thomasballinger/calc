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
        elif s == '%': return Token('Percent', s, start, end)
        elif s == '(': return Token('Left Paren', s, start, end)
        elif s == ')': return Token('Right Paren', s, start, end)
        elif s == '>': return Token('Greater', s, start, end)
        elif s == '=': return Token('Equals', s, start, end)
        elif s == '<': return Token('Less', s, start, end)
        elif s == ';': return Token('Semi', s, start, end)
        elif s == ',': return Token('Comma', s, start, end)
        elif s == '.': return Token('Dot', s, start, end)
        elif s == 'if': return Token('If', s, start, end)
        elif s == 'then': return Token('Then', s, start, end)
        elif s == 'else': return Token('Else', s, start, end)
        elif s == 'while': return Token('While', s, start, end)
        elif s == 'do': return Token('Do', s, start, end)
        elif s == 'end': return Token('End', s, start, end)
        elif s == 'run': return Token('Run', s, start, end)
        elif s == 'compile': return Token('Run', s, start, end)
        elif s == 'return': return Token('Return', s, start, end)
        elif s == 'class': return Token('Class', s, start, end)
        elif s == 'extends': return Token('Extends', s, start, end)
        elif s[0] == '"' and s[-1] == '"': return Token('String', s[1:-1], start, end)
        elif s.isnumeric(): return Token('Number', int(s), start, end)
        elif s[0].isalpha() and s.isalnum(): return Token('Variable', s, start, end)
        else: raise ValueError("Can't parse string '{}' into token".format(s))

    def __repr__(self):
        if self.kind in ("Number", "Variable"):
            return f"Token(kind='{self.kind}', content={repr(self.content)})"
        elif self.kind == "String":
            return f'"{self.content}"'
        return f"Token(kind='{self.kind}')"

def tokenize(string):
    """
    >>> tokenize('1 - 22')
    [Token(kind='Number', content=1), Token(kind='Minus'), Token(kind='Number', content=22)]
    >>> tokenize('abc')
    [Token(kind='Variable', content='abc')]
    """
    tokens = []
    token_string = ''
    in_string = False
    for i, c in enumerate(string):
        if c == '"':
            if in_string:
                token_string += c
                tokens.append(Token.from_string(token_string, i-len(token_string)))
                token_string = ''
            else:
                token_string += c
            in_string = not in_string
        elif in_string:
            token_string += c
        elif c in (' ', '\n'):
            if token_string:
                tokens.append(Token.from_string(token_string, i-len(token_string)))
                token_string = ''
            token_string = ''
        elif c in ('+', '-', '*', '/', '%', '(', ')', '>', '<', '=', ';', ',', '.'):
            if token_string:
                tokens.append(Token.from_string(token_string, i-len(token_string)))
                token_string = ''
            tokens.append(Token.from_string(c, i))
        elif c.isnumeric():
            token_string += c
        elif c.isalpha():
            token_string += c
        else:
            raise ValueError('Unknown character: {}'.format(c))

    if token_string:
        tokens.append(Token.from_string(token_string, i-len(token_string)))

    return tokens

if __name__ == '__main__':
    import doctest
    doctest.testmod()
