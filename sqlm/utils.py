import re

_TK_RE = re.compile(r"""("""
                    r"""(?:^[!@]+)"""               # leading special symbols
                    r"""|"""
                    r"""(?:[\[\]])"""               # backets
                    r"""|"""
                    r"""(?:'(?:[^']|[']['])*'(?=]?(?:\s|$)))"""  # single quotes + SQL escape
                    r"""|"""
                    r"""(?:"[^"]*"(?=]?(?:\s|$)))"""      # double quotes
                    r"""|"""
                    r"""(?:[^'"\s]+?(?=]?(?:\s|$)))"""     # non-space non quotes
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

def _parse(tokens):
    """Build a tree representation of a tokenized expressions
    """
    stk = []
    expr = []
    for token in tokens:
        if token == '[':
            stk.append(expr)
            expr = []
        elif token == ']':
            subexpr = tuple(expr)
            expr = stk.pop()
            expr.append(subexpr)
        else:
            expr.append(token)

    if stk:
        raise ValueError("Unbalanced brackets")

    return tuple(expr)

def parse(pattern):
    """Parse a pattern expressed as a string.
    """

    return _parse(tokenize(pattern))
            

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

    return tuple(_unquote(tk) for tk in t[1:-1:2])

def _unify(pattern, tokens, bound = {}):
    """Try to unify a pattern with a list of tokens.

    Both must be expressed as sequences.
    """
    #print(pattern, tokens, bound)
    if not pattern and not tokens:
        return bound, ()

    if pattern:
        hp, *pattern = pattern
        if type(hp) != str:
            # Not a string. Assume an optional sub-expression
            
            # First try to parse with the optional sub-expression:
            ans, tail = _unify(hp, tokens, bound)
            if ans is not None:
                ans, tail = _unify(pattern, tail, ans)
                if ans is not None:
                    return ans, tail

            # If we reach this point, we can't find a match with the
            # sub-expression. Ignore it and continue.
            return _unify(pattern, tokens, bound)


        occ = '1'
        occ_min = 1
        occ_max = 1
        if hp[-1:] == '?':
            hp = hp[:-1]
            occ = '?'
            occ_min = 0
        elif hp[-1:] == '*': # XXX we should implement unbound list by
                             # using infinitly nested lists
            hp = hp[:-1]
            occ = '*'
            occ_min = 0
            occ_max = len(tokens)

        # if len(tokens) < occ_min:
        #    return None, None
        
        for n in range(occ_max, occ_min-1,-1):
            #print(n)
            tk = tokens[:n]
            bv = [hp]*n
            nbound = bound
            if hp.isalpha():
                if hp.isupper():
                    tk = [i.upper() for i in tk]
                    bv = [hp]*n
                elif hp.islower():
                    bv = bound.get(hp)
                    if bv is None:
                        nbound = bound.copy()
                        bv = tk
                        nbound[hp] = (occ,bv)
                    else:
                        bv = bv[1]

            #print(tk,bv)
            if tk == bv:
                ans, ntokens = _unify(pattern, tokens[n:], nbound)
                if ans is not None:
                    return ans, ntokens

    return None, None

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

    ans, tail = _unify(pattern, tokens)
    if ans is None:
        return None

    return {k: v[1] if v[0] == '*'
               else v[1][0] if v[0] == '1'
               else (v[1] or (None,))[0] for k, v in ans.items()}


class TokenSeq:
    def __init__(self, stmt):
        self._tokens = parse(stmt)

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


