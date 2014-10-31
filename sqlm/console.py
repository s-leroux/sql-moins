class Console:
    def run(self, interpreter):
        try:
            while True:
                self.interact(interpreter)
        except EOFError:
            print()

    def interact(self, interpreter):
        statement = input('SQL> ')
        interpreter.eval(statement)
