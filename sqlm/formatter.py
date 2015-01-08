import functools

class TabularFormatter:
    def display(self, env, result):
        # print(result.keys())
        
        # See http://legacy.python.org/dev/peps/pep-0249/#cursor-attributes
        # for cursor.description fields
        # print([item for item in result.cursor.description])
        keys = result.keys()
        w = [len(str(item)) for item in keys]

        data = []
        for row in result:
            row = [item if item is not None else "(null)" for item in row]
            w = [max(i[0],len(str(i[1]))) for i in zip(w,row)]
            data.append(row)

        fmt = " " + " | ".join(["{:"+str(item)+"}" for item in w]) + " "
        sep = "-" + "-+-".join(["-"*item for item in w])           + "-"

        #print(data)
        #print(fmt)
        print(fmt.format(*keys))
        print(sep)
        for row in data:
            print(fmt.format(*row))
            
