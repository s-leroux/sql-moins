import sys
import sqlalchemy

class ArgumentError(Exception):
    def __init__(self, message):
        super(ArgumentError, self).__init__(message)

class Interpreter:
    def __init__(self):
        self.engine = None
        self.commands = {
                'QUIT': self.doQuit,
                'CONNECT': self.doConnect
        }

    def eval(self, statement):
        args = statement.split() # XXX Maybe we should be smarter here (quotes?)

        if args: # Ignore blank lines
            cmd = self.commands.get(args[0].upper(), self.doDefault)
            try:
                result = cmd(statement, *args[1:])
                if result:
                    print("ok -", result)
            except ArgumentError as err:
                print("Error: command", args[0], file=sys.stderr)
                print("   ", err.args[0], file=sys.stderr)

    def doQuit(self, statement, *args):
        if len(args) > 0:
            raise ArgumentError("No argument required")

        raise EOFError

    def doConnect(self, statement, *args):
        if len(args) != 1:
            raise ArgumentError("Usage: connect url")

        (url, ) = args
        self.engine = sqlalchemy.create_engine(url)
        return self.engine

    def doDefault(self, statement, *args):
        self.engine.execute(statement)
        pass
