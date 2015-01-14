from types import SimpleNamespace
import functools

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
        self.align = '>' if self.type_code in ('NUMBER') else '<'

    def get_format(self):
        """Return the format used to display that column properly
        """
        return "{{!s:{align}{display_size}}}".format(**self.__dict__)

    def blank(self, pattern = '-'):
        """
        Return a "blank field" of the right width.
        This could be used to generate place-holders and/or separators.
        """
        return (pattern*self.display_size)[0:self.display_size]

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
            
