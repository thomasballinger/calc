from collections import namedtuple
from num2words import num2words

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
        elif s == '<': return Token('Less', s)
        elif s == '=': return Token('Equals', s)
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

BinaryOp = namedtuple('BinaryOp', ['left', 'op', 'right'])
UnaryOp = namedtuple('UnaryOp', ['op', 'right'])

def pprint_tree(node, indent=2):
    if isinstance(node, Token):
        print(' '*indent + str(node.content))
    elif isinstance(node, BinaryOp):
        print(' '*indent + node.op.content)
        pprint_tree(node.left, indent + 2)
        pprint_tree(node.right, indent + 2)
    elif isinstance(node, UnaryOp):
        print(' '*indent + node.op.content)
        pprint_tree(node.right, indent + 2)

def parse(tokens):
    tree, unused_tokens = parse_greater_or_less(tokens)
    if unused_tokens:
        raise ValueError("Trailing unparsed tokens: {}".format(unused_tokens))
    return tree

def parse_greater_or_less(tokens):
    expr, remaining_tokens = parse_plus_or_minus(tokens)

    if remaining_tokens and remaining_tokens[0].kind in ('Greater', 'Less'):
        op, *remaining_tokens = remaining_tokens
        right, remaining_tokens = parse_plus_or_minus(remaining_tokens)
        expr = BinaryOp(expr, op, right)

    return expr, remaining_tokens

def parse_plus_or_minus(tokens):
    expr, remaining_tokens = parse_multiply_or_divide(tokens)

    while remaining_tokens and remaining_tokens[0].kind in ('Plus', 'Minus'):
        op, *remaining_tokens = remaining_tokens
        right, remaining_tokens = parse_multiply_or_divide(remaining_tokens)
        expr = BinaryOp(expr, op, right)

    return expr, remaining_tokens

def parse_multiply_or_divide(tokens):
    expr, remaining_tokens = parse_operand(tokens)

    while remaining_tokens and remaining_tokens[0].kind in ('Star', 'Slash'):
        op, *remaining_tokens = remaining_tokens
        right, remaining_tokens = parse_operand(remaining_tokens)
        expr = BinaryOp(expr, op, right)

    return expr, remaining_tokens

def parse_unary_op(tokens):
    op, *remaining_tokens = tokens
    assert op.kind in ('Plus', 'Minus', 'Print', 'String', 'Length')
    operand, remaining_tokens = parse_operand(remaining_tokens)
    expr = UnaryOp(op=op, right=operand)

    return expr, remaining_tokens

def parse_operand(tokens):
    if tokens[0].kind == 'Number':
        expr, *remaining_tokens = tokens
        return expr, remaining_tokens
    elif tokens[0].kind in ('Minus', 'Plus', 'Print', 'String', 'Length'):
        expr, remaining_tokens = parse_unary_op(tokens)
        return expr, remaining_tokens
    elif tokens[0].kind == 'Left Paren':
        _, *remaining_tokens = tokens
        expr, remaining_tokens = parse_greater_or_less(remaining_tokens)
        right_paren, *remaining_tokens = remaining_tokens
        if not right_paren.kind == 'Right Paren':
            raise ValueError('Expected {} to be a right paren'.format(right_paren))
        return expr, remaining_tokens
    else:
        raise ValueError("Can't parse tokens: {}".format(tokens))

binary_funcs = {
    'Plus': lambda x, y: x+y,
    'Minus': lambda x, y: x-y,
    'Star': lambda x, y: x*y,
    'Slash': lambda x, y: x/y,
    'Greater': lambda x, y: x > y,
    'Less': lambda x, y: x < y,
}
unary_funcs = {
    'Plus': lambda x: x,
    'Minus': lambda x: -x,
    'Print': lambda x: (print(x), x)[1],
    'String': num2words,
    'Length': len,
}

def evaluate(node):
    if isinstance(node, Token):
        return node.content
    elif isinstance(node, BinaryOp):
        return binary_funcs[node.op.kind](evaluate(node.left), evaluate(node.right))
    elif isinstance(node, UnaryOp):
        return unary_funcs[node.op.kind](evaluate(node.right))

def debug_repl():
    while True:
        try:
            s = input('> ')
            tokens = tokenize(s)
            print(repr(tokens))
            tree = parse(tokens)
            print(repr(tree))
            pprint_tree(tree)
            print(evaluate(tree))
        except ValueError as e:
            print(e)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
    debug_repl()
