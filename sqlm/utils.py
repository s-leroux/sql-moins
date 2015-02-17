import re

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


