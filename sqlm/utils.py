import re

_TK_RE = re.compile(r"""("""
    r"""(?:^[!@]+)"""               # leading special symbols
    r"|"
    r"""(?:[\[\]])"""               # backets
    r"|"
    r"""(?:\.\.\.)"""               # ellipsis
    r"|"
    # single quotes + SQL escape
    r"(?:" r"""'(?:[^']|[']['])*'""" r"(?=]?(?:\.\.\.)?(?:\s|$))" r")"  
    r"|"
    # double quotes
    r"(?:" r'''"[^"]*"'''            r"(?=]?(?:\.\.\.)?(?:\s|$))" r")"
    r"|"
    # non-space non quotes
    r"(?:" r"""[^'"\s]+?"""          r"(?=]?(?:\.\.\.)?(?:\s|$))" r")"
    r")")

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

def _quantifiers(tokens):
    """Returns a dictionary containing
    the quantifier corresponding to each variable in the pattern
    """

    result = {}
    stk = []
    min_occ = 1
    max_occ = 1
    saved_max = 1

    for token in tokens[::-1]:
        if token.isalpha() and token.islower():
            prev_min, prev_max = result.get(token, (0,0))
            #if prev_min < min_occ:
            #    min_occ = prev_min
            #if prev_max > max_occ:
            #    max_occ = prev_max
            result[token] = (min_occ+prev_min, max_occ+prev_max)
            max_occ = saved_max

        elif token == ']':
            stk.append((min_occ, saved_max))
            min_occ = 0
            saved_max = max_occ
        elif token == '[':
            min_occ, max_occ = stk.pop()
            saved_max = max_occ
        elif token == '...':
            saved_max = max_occ
            max_occ = 1000 # arbitrary number. Anything > 1 will work
        else:
            max_occ = saved_max

    return result

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
            subexpr = expr
            expr = stk.pop()
            expr.append(subexpr)
        elif token == '...':
            subexpr = expr[-1]
            if type(subexpr) == str:
                # One or many
                subexpr = [subexpr]
            else:
                expr = expr[:-1] # pop it

            # Then buidl an infinitly nested list
            subexpr.append(subexpr)
            expr.append(subexpr)
        else:
            expr.append(token)

    if stk:
        raise ValueError("Unbalanced brackets")

    return expr

def parse(pattern):
    """Parse a pattern expressed as a string.
    """

    if type(pattern) == str:
        pattern = tokenize(pattern)

    return _parse(pattern), _quantifiers(pattern)
            

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

def _unify(pattern, tokens, bound = ()):
    """Try to unify a pattern with a list of tokens.

    Both must be expressed as sequences.
    """
    #print(pattern, tokens, bound)
    if not pattern:
        return bound, tokens

    hp, *pattern = pattern
    if type(hp) != str:
        # Not a string. Assume an optional sub-expression
        
        # try to parse with the optional sub-expression:
        hp = hp[:] + pattern
        ans, tail = _unify(hp, tokens, bound)

        if tail == []:
            return ans, tail

        # If we reach this point, we can't find a match with the
        # sub-expression. Ignore it and continue.
        return _unify(pattern, tokens, bound)

    elif tokens:
        tk, *tokens = tokens
        rec = (hp is pattern)

        if hp.isalpha():
            if hp.isupper():
                tk = tk.upper()
            elif hp.islower():
                bound = ((hp, tk), bound)
#                bound = bound.copy() # Copy it !!
#                bv = bound.get(hp, [])
#                bound[hp] = [tk, bv]
#                bv = bv.copy() # Copy it !!!
#                if bv is not None:
#                    if type(bv) is str:
#                        bv = [bv]
#                    else:
#                        bv = bv.copy() # Copy it !!!
#                    bv.append(tk)
#                    bound[hp] = bv
#                else:
#                    bound[hp] = tk

                tk = hp # Force success of the following test

        if hp == tk:
            return _unify(pattern, tokens, bound)


    return None, None

def _unwind(cons, quantifiers = {}):
    result = {}
    while cons:
        (k,v), cons = cons
        
        entry = result.setdefault(k, [])
        entry.append(v)

    for k, v in result.items():
        if quantifiers.get(k , (0,9999))[1] == 1:
            result[k] = v[0]
        else:
            result[k] = v[::-1]

    return result

class ParsedPattern:
    def __init__(self, stmt):
        tokens = tokenize(stmt)

        self._pattern = _parse(tokens)
        self._qty = _quantifiers(tokens)

    def unify(self, stmt):
        if type(stmt) == str:
            stmt = tokenize(stmt)

        ans, tail =  _unify(self._pattern, stmt)

        if ans is None or tail:
            return None

        return _unwind(ans, self._qty)


def compile(stmt):
    return ParsedPattern(stmt)

def unify(pattern, stmt):
    matcher = compile(pattern)
    return matcher.unify(stmt)

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


