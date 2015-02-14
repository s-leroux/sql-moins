import re

_TK_RE = re.compile(r"""("""
                    r"""(?:^[!@]+)"""               # leading special symbols
                    r"""|"""
                    r"""(?:'(?:[^']|[']['])*'(?=\s|$))"""  # single quotes + SQL escape
                    r"""|"""
                    r"""(?:"[^"]*"(?=\s|$))"""      # double quotes
                    r"""|"""
                    r"""(?:[^'"\s]+(?=\s|$))"""     # non-space non quotes
                    r""")""")

def _unquote(tk):
    """Remove quotes from a string. Perform required substitutions.

    - Enclosing quotes are removed
    - double-single-quotes are replaced by single quote in single quoted strings
      (i.e:  'abc''def' => abc'def)
    """
    if not tk:
        return tk

    if tk[0] == tk[-1] == '"':
        return tk[1:-1]

    if tk[0] == tk[-1] == "'":
        return tk[1:-1].replace("''","'")

    return tk

def tokenize(stmt):
    """tokenize a statement.

    Returns a list of the 'words' of the statement.
    Quoted string are considered as one word"""

    t = _TK_RE.split(stmt.lstrip())
    # at this point:
    # - t[n] is a (possibly empty) sequence of spaces
    # - t[n+1] is a token
    #
    # if t[n] is not empty but does not contains only spaces, 
    # the statement is ill formed
    # (missing quote/unbalanced quotes) and will raise ValueError

    for sep in t[::2]:
        if sep and not sep.isspace():
            raise ValueError("Unbalanced quotes" + str(t))

    return [_unquote(tk) for tk in t[1:-1:2]]

def unify(pattern, tokens):
    """Try to unify a pattern with a list of tokens.

    Returns a dictionnary containing the bound variables.

    All uppercase letters-only tokens in the pattern are assumed to
    be keywords and are case insensitive.

    All lowercase letters-only tokens are assumed to be bound variable.
    They are matched case-sensitive.

    All other tokens are case-sensitive matched

    example:
       unify("SET attr TO value", "SET V TO abc")

    will return { 'attr':'V', 'value':'abc'}

    Unification will work as expected in case of multiple occurence
    of the same bind values.
    """
    if type(pattern) == str:
        pattern = tokenize(pattern)

    if type(tokens) == str:
        tokens = tokenize(tokens)

    if len(pattern) != len(tokens):
        raise ValueError("Mismatch between pattern and tokens length")

    result = {}
    for p, tk in zip(pattern, tokens):
        if p.isalpha():
            if p.isupper():
                tk = tk.upper()
            elif p.islower():
                k = p
                p = result.get(k)
                if p is None:
                    result[k] = p = tk
        
        if p != tk:
            raise ValueError("Can't match: " + p +" " + tk)
                
    
    return result


class TokenSeq:
    def __init__(self, stmt):
        self._tokens = tokenize(stmt)

    def unify(self, stmt):
        return unify(self._tokens, stmt)

def compile(stmt):
    return TokenSeq(stmt)


_NS_RE = re.compile('([-+]?[0-9]+)(?:-([-+]?[0-9]+))?')

def numSelector(sel):
    """Generator returning each value in a number selector.

    Mini-language grammar:

    <expr> := <num>     an integer (possibly signed)
            | <n1>-<n2> range from n1 to n2 incl.
            | <expr1> <expr2> expr1 then expr2
    """
    if type(sel) is str:
        sel = sel.split()

    for expr in sel:
        m = _NS_RE.match(expr)
        if not m:
            raise ValueError("Invalid selector " + repr(str(expr)))

        n1 = m.group(1)
        n2 = m.group(2)
        if n2 is None:
            n2 = n1

        n1 = int(n1)
        n2 = int(n2)

        if n2 < n1:
            r = range(n1,n2-1,-1)
        else:
            r = range(n1, n2+1)

        for n in r:
            yield n


