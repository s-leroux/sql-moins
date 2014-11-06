import os
import sys
import atexit
import readline
import traceback

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
    def run(self, interpreter, env):
        quit = False

        while not quit:
            try:
                self.interact(interpreter)
            except EOFError:
                quit = True
                print()
            except Exception as err:
                env.reportError(err)

    def interact(self, interpreter):
        prompt = 'SQL> '
        n = 1
        while True:
            line = input(prompt)
            if interpreter.push(line) == 0:
                break

            n += 1
            prompt = '{:3d}  '.format(n)

