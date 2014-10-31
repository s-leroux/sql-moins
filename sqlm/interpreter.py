import sys

class ArgumentError(Exception):
    def __init__(self, message):
        super(ArgumentError, self).__init__(message)

class Interpreter:
    def __init__(self):
        self.commands = {
                'QUIT': self.doQuit,
                'CONNECT': self.doConnect
        }

    def eval(self, statement):
        args = statement.split() # XXX Maybe we should be smarter here (quotes?)

        if args: # Ignore blank lines
            cmd = self.commands.get(args[0].upper(), self.doDefault)
            try:
                cmd(*args)
            except ArgumentError as err:
                print("Error: command", args[0], file=sys.stderr)
                print("   ", err.args[0], file=sys.stderr)

    def doQuit(self, *args):
        if len(args) > 1:
            raise ArgumentError("No argument required")

        raise EOFError

    def doConnect(self, *args):
        pass

    def doDefault(self, *args):
        pass
