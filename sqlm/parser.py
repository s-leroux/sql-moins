"""Simple pattern matcher for man-like command synopsis.

A synopsis pattern is made of several kind of tokens:

- place-holders : words spelled in lower cases are assumed to
    be place-holders for user supplied values. The same
    place-holder might appends several times in the same
    synopsis. In that case all user supplied values are returned
    in a list
- keywords : words spelled in upper cases are assumed to be
    keywords. They are matched case unsensitive.
- [ pattern ] : a pattern enclosed in brackets is optional.
- ... : elipsis denotes one or more repetition of the preceeding token

Example:
    EDIT filename [FOR event...]
    SET attr [TO] value
    HOST cmd [args]...


"""

import re

#: Regular expression used by the tokenizer to break
#: a string into tokens
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
    - SQL-like escape sequence in single quotes are replaced by
      their value (i.e:  'abc''def' => abc'def)
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

    Returns a list of the 'tokens' of the statement.
    Quoted string are considered as one token. In the later,
    enclosing quotes are removed and metacharacters are replaced
    by their value..
    """

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

def _parse(tokens):
    """Build a hierarchical representation of a tokenized expressions.


    Args:
      tokens (sequence): a sequence of tokens

    Raises:
      ValueError: if the brackets are not balanced in the 
        tokenized expression

    Exemple:
      ("HOST", "cmd", "[", "args", "]", "...") 
        => ["HOST", "cmd", ["args", [...]]]

      (note: unbound repetitions are implemented 
       using infinitly recursive lists)
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

def _quantifiers(tokens):
    """Inspect a list of tokens and for each place-holder
    return in a dictionary the minimum and an estimate of 
    the maximum possible number of occurences in a valid 
    expression.

    The minimum is always accurate. Maximum is accurate
    only if it is 1 or is equal to the minimum.

    The main purpose of this function is to be able to distinguish
    between `unique`, `optional` or `multiple` arguments.

    Args:
      tokens (sequence): a sequence of tokens as parsed by tokenize

    Example:
      (using string for ease of representation):
      HOST cmd [args]... => {cmd: (1,1), args:(0, 9999)}
      PRINT str [ , str] => {str: (1, 9999)}

      WHATEVER x x x => {x: (3,3)}

    
    and an estimate of thReturns a dictionary containing
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

def _match(pattern, tokens, bound = ()):
    """Try to match a pattern with a sequence of tokens.

    Args:
      pattern (sequence): a pattern as returned by _parse
      tokens  (sequence): a sequence of tokens as returned by tokenize

    Returns:
      None, _ : if the tokens do not match with the given pattern
      {..}, "": a dictionnary defining the mapping between pattern
                place-holders and token(s). Multiple values are 
                expressed as nested tuples (LISP-style cons list)
    """
    #print(pattern, tokens, bound)
    if not pattern:
        if tokens:
            # Pattern exhausted but token list not empty
            return None, None

        return bound, tokens

    hp, *pattern = pattern
    if type(hp) != str:
        # Not a string. Assume an optional sub-expression
        
        # try to parse with the optional sub-expression:
        hp = hp[:] + pattern
        ans, tail = _match(hp, tokens, bound)

        if tail == []:
            return ans, tail

        # If we reach this point, we can't find a match with the
        # sub-expression. Ignore it and continue.
        return _match(pattern, tokens, bound)

    elif tokens:
        tk, *tokens = tokens
        rec = (hp is pattern)

        if hp.isalpha():
            if hp.isupper():
                tk = tk.upper()
            elif hp.islower():
                bound = ((hp, tk), bound)

                tk = hp # Force success of the following test

        if hp == tk:
            return _match(pattern, tokens, bound)


    return None, None

def _unwind(cons, quantifiers = {}):
    """Unwind a nested LISP-style list to a Python-style
    data structure.

    The quantifiers argument is used to choose between a list
    representation (if max occurence count > 1) or a scalar
    value (max occurence count == 1).

    Example:
      unwind( (('x', 1), (('y', 2), (('x', 3), ()))) ) 
       => { 'x':[1,3], 'y':[2] }
    """
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

class Synopsis:
    """A compiled representation of the sysnopsis of a command

    """

    def __init__(self, stmt):
        """Initialize a new Synopsis instance from its string representation.

        Raises:
          ValueError: if the string is not syntactically correct
            (unbalanced quotes, unbalanced brackets, ...)
        """
        tokens = tokenize(stmt)

        self._pattern = _parse(tokens)
        self._qty = _quantifiers(tokens)

    def match(self, stmt):
        """Try to match the current synopsis with a given string or
        sequence of tokens
        """
        if type(stmt) == str:
            stmt = tokenize(stmt)

        ans, tail =  _match(self._pattern, stmt)

        if ans is None:
            return None

        return _unwind(ans, self._qty)

def compile(stmt):
    """Return a newly created Synopsis object
    corresponding to the statement
    """
    return Synopsis(stmt)

def unify(pattern, stmt):
    synopsis = compile(pattern)
    return synopsis.match(stmt)
