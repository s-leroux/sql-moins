import sys

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
