class Console:
    def run(self):
        try:
            while True:
                self.interact()
        except EOFError:
            print()

    def interact(self):
        input('SQL> ')
