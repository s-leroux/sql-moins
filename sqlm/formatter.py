from types import SimpleNamespace
from decimal import Decimal
import functools
import re

def decimal_tuple(d):
    """
    Return a tupple (sign, integral, fractional)
    corresponding to the given decimal number.

    This is different from the `as_tuple` method that
    returns the mantisa and the exponent
    """
    sign, digits, exponent = d.normalize().as_tuple()
    n = len(digits)+exponent
    if n < 0:
        digits = (0,)*-n + digits

    if not exponent:
        exponent = len(digits)

    return sign, digits[:exponent], digits[exponent:]
    

class FormatError(ValueError):
    def __init__(self, c, msg='format'):
        super().__init__("Invalid character {!r} in {} model".format(c, msg))

def _to_char_number(value, fmt):
    """
    Format a value using a *number* format
    """
    result=''
    sign, integral, fractional = decimal_tuple(Decimal(value))
    pos = dotidx = fmt.find('.')

    if pos < 0:
        pos = len(fmt)
    else:
        result = '.'

    lpad = ' '
    fill = ' '

    if pos > 0:
        for c in fmt[pos-1::-1]:
            if c == '9':
                if integral:
                    *integral, n = integral
                    result = str(n) + result
                else:
                    fill = lpad + fill
            elif c in ('+','-'):
                fill = fill[:-1]+ ('-' if sign else '+')
            elif c == ',':
                if integral:
                    result = ',' + result
                else:
                    fill = lpad + fill
            else:
                raise FormatError(c, 'number format')

    result = fill + result

    if dotidx >= 0:
        n = None
        for c in fmt[dotidx+1:]:
            if c == '9':
                if fractional:
                    n, *fractional = fractional
                    result = result + str(n)
                else:
                    result += '0'
            else:
                raise FormatError(c, 'number format')
       
        # round last digit to the nearest
        if fractional and fractional[0] >= 5 and n is not None:
            result = result[:-1] + str(n+1)

    if integral:
        return '#' * len(result)
    else:
        return result


def _to_char_string(value, fmt):
    """
    Format a value using a *string* format
    """
    value = str(value)
    n = 0
    for c in fmt:
        if c == 'X':
            n += 1
        else:
            raise FormatError(c, 'string format')

    return value[0:n].rjust(n, ' ')

def to_char(value, fmt):
    """
    Oracle-like TO_CHAR function.

    Support numbers and string formats

    Number
    ======
    9999    Number prefixed with a space for positive numbers,
            '-' for negative numbers

    Strings
    =======
    'X'* space (left) padded string 
    """
    if not fmt:
        return ''

    if fmt[0] in ('X'):
        return _to_char_string(value, fmt)
    elif fmt[0] in ('9','+','-', '.'):
        return _to_char_number(value, fmt)
    else:
        raise FormatError(fmt[0])

class Column(SimpleNamespace):
    # http://legacy.python.org/dev/peps/pep-0249/#cursor-attributes
    def __init__(self, name, type_obj, 
                             display_size, 
                             internal_size,
                             precision,
                             scale,
                             null_ok):

        # Mandatory arguments
        self.name = name
        self.type_obj = type_obj
        self.type_code = type_obj.__name__

        # Optional arguments
        self.display_size = display_size or 0
        self.internal_size = internal_size or 0
        self.precision = precision or 0
        self.scale = scale or 0
        self.null_ok = null_ok or True # Shouldn't we assume the worst 
                                       # case here ?

        # Computed values
        self.align = '>' if self.isNumber() else '<'

    def isNumber(self):
        return self.type_code in ('NUMBER')

    def getFormat(self):
        """Return the format used to display that column properly
        """
        return "{{!s:{align}{display_size}}}".format(**self.__dict__)

    def blank(self, pattern = '-'):
        """
        Return a "blank field" of the right width.
        This could be used to generate place-holders and/or separators.
        """
        return (pattern*self.display_size)[0:self.display_size]

class Page:
    """
    A page of data.

    Serves as a cache for data and to adjust format according to the
    actual values.

        -1235.67
            1.5
          240
        ^      ^
        |      | display_width
             ^
             |   ref pos
        ^   ^
        |   |    left part (right aligned)
              ^^
              || right part (left aligned)

    """

    def __init__(self, columns, null='NULL'):
        self.rows = []
        self.null = null
        self.columns = columns[:]

    def append(self, row):
        self.rows.append(row)
                
    def formats(self):
        result = [ ]

        for c, values in zip(self.columns, [i for i in zip(*self.rows)]):
            if c.isNumber():
                left = right = 0
                hasNull = False
                for value in values:
                    if value is None:
                        hasNull = True
                    else:
                        sign, digits, exponent = Decimal(value).as_tuple()

                        if right < -exponent:
                            right = -exponent
                        if left < max(0,len(digits) + exponent):
                            left = max(0,len(digits) + exponent)

                fmt = '+'+'9'*left + '.' + '9'*right
                if hasNull and len(fmt) < len(self.null):
                    fmt = ' '*len(self.null)-len(fmt) + fmt
            else:
                w = 0
                for value in values:
                    if value is None:
                        value = self.null

                    w = max(w, len(value))

                fmt = 'X'*w

            result.append(fmt)

        return result


def make_columns(cursor_description):
    return [Column(*desc) for desc in cursor_description]

class TabularFormatter:
    def display(self, env, result):
        # print(result.keys())
        
        # See http://legacy.python.org/dev/peps/pep-0249/#cursor-attributes
        # for cursor.description fields
        # print([item for item in result.cursor.description])

#        colnum = len(result.cursor.description)
#
#        columns = [SimpleNamespace(name=name, 
#                                    type_code=col_type.__name__,
#                                    width=1,
#                                    align='>' if col_type.__name__ in ('NUMBER') else '<')
#                     for name, col_type, *tail in result.cursor.description]
#
#        keys = result.keys()
#        wl = [len(str(item)) for item in keys]
#
#        data = []
#        for row in result:
#            row = [item if item is not None else "(null)" for item in row]
#            for col, value in zip(columns, row):
#                w = len(str(value))
#                col.width = max(col.width, w)
#            data.append(row)
#
#        fmt_list = []
#        for idx, column in enumerate(columns):
#            w = column.width
#
#            fmt_list.append("{!s:"+column.align + str(w)+"}")
#
#        print(columns)
#
#        fmt = " " + " | ".join(fmt_list) + " "
#        sep = "-" + "-+-".join(["-"*item for item in wl])           + "-"

        keys = result.keys()
        columns = make_columns(result.cursor.description)
        fmt = " " + " | ".join(map(Column.get_format, columns)) + " "
        sep = "-" + "-+-".join(map(Column.blank, columns))      + "-"

        data = []
        for row in result: # prefetch data -- NOT NEEDED !!! 
            data.append(row)

        #print(data)
        #print(fmt)
        print(fmt.format(*keys))
        print(sep)
        for row in data:
            #print(row)
            print(fmt.format(*row))
            
