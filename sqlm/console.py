import os
import sys
import atexit
import readline

#
# from https://docs.python.org/3/library/readline.html#example
#
histfile = os.path.join(os.path.expanduser("~"), ".sqlmoins_history")
try:
    readline.read_history_file(histfile)
except FileNotFoundError:
    pass

atexit.register(readline.write_history_file, histfile)

class Console:
    def run(self, interpreter):
        quit = False
        while not quit:
            try:
                self.interact(interpreter)
            except EOFError:
                quit = True
                print()
            except Exception as err:
                print(err, file=sys.stderr)

    def interact(self, interpreter):
        statement = input('SQL> ')
        interpreter.eval(statement)
