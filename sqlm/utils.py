import re

_TK_RE = re.compile(r"""("""
                    r"""(?:'(?:[^']|[']['])*')"""  # single quotes + SQL escape
                    r"""|"""
                    r"""(?:"[^"]*")"""             # double quotes
                    r"""|"""
                    r"""(?:[^'"\s]+)"""            # non-space non quotes
                    r""")""")

def _unquote(tk):
    """Return a normalized representation of a token.

    - Non-quotes strings are converted to uppercase
    - Enclosing quotes are removed
    - double-single-quotes are replaced by single quote in single quote strings
      (i.e:  'abc''def' => 'abc'def')
    """
    if not tk:
        return tk

    if tk[0] == tk[-1] == '"':
        return tk[1:-1]

    if tk[0] == tk[-1] == "'":
        return tk[1:-1].replace("''","'")

    return tk.upper()

def tokenize(stmt):
    """tokenize a statement.

    Returns a list of the 'words' of the statement.
    Quoted string are considered as one word"""

    t = _TK_RE.split(" " + stmt + " ")
    # at this point:
    # - t[n] is a (non empty) sequence of spaces
    # - t[n+1] is a token
    #
    # if any inner t[n] is empty, the statement is considered as ill formed
    # (missing separator) and will raise ValueError
    # if t[n] does not contains only spaces, the statement is ill formed
    # (missing quote/unbalanced quotes) and will raise ValueError

    for sep in t[::2]:
        if not sep:
            raise ValueError("Missing seperator " + str(t))
        elif not sep.isspace():
            raise ValueError("Unbalanced quotes" + str(t))

    return [_unquote(tk) for tk in t[1:-1:2]]

def unify(pattern, tokens):
    """Try to unify a pattern with a list of tokens.

    Returns a dictionnary containing the matching values.

    example:
       unify("SET :attr TO :value", "SET V TO 1")

    will return { 'ATTR':'V', 'VALUE':'1'}

    Unification will work as expected in case of multiple bind values.
    """
    if type(pattern) == str:
        pattern = tokenize(pattern)

    if type(tokens) == str:
        tokens = tokenize(tokens)

    if len(pattern) != len(tokens):
        raise ValueError("Mismatch between pattern and tokens length")

    result = {}
    for p, tk in zip(pattern, tokens):
        if p.startswith(':'):
            k = p[1:]
            p = result.get(k)
            if p is None:
                result[k] = p = tk
        
        if p != tk:
            raise ValueError("Can't match: " + p +" " + tk)
                
    
    return result


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


