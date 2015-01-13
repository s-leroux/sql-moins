from types import SimpleNamespace
import functools

class TabularFormatter:
    def display(self, env, result):
        # print(result.keys())
        
        # See http://legacy.python.org/dev/peps/pep-0249/#cursor-attributes
        # for cursor.description fields
        # print([item for item in result.cursor.description])

        colnum = len(result.cursor.description)

        columns = [SimpleNamespace(name=name, 
                                    type_code=col_type.__name__,
                                    width=1,
                                    align='>' if col_type.__name__ in ('NUMBER') else '<')
                     for name, col_type, *tail in result.cursor.description]

        keys = result.keys()
        wl = [len(str(item)) for item in keys]

        data = []
        for row in result:
            row = [item if item is not None else "(null)" for item in row]
            for col, value in zip(columns, row):
                w = len(str(value))
                col.width = max(col.width, w)
            data.append(row)

        fmt_list = []
        for idx, column in enumerate(columns):
            w = column.width

            fmt_list.append("{!s:"+column.align + str(w)+"}")

        print(columns)

        fmt = " " + " | ".join(fmt_list) + " "
        sep = "-" + "-+-".join(["-"*item for item in wl])           + "-"

        #print(data)
        #print(fmt)
        print(fmt.format(*keys))
        #print(sep)
        for row in data:
            #print(row)
            print(fmt.format(*row))
            
