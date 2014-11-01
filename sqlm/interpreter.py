import sys
import re
from getpass import getpass
import sqlalchemy

class ArgumentError(Exception):
    def __init__(self, message):
        super(ArgumentError, self).__init__(message)

class Command:
    def __init__(self):
        self.buffer = []

    def statement(self):
        return '\n'.join(self.buffer)

class InternalCommand(Command):
    def push(self, line):
        self.buffer.append(line)
        return True

    def run(self, interpreter):
        interpreter.eval(self.statement())

class OtherCommand(Command):
    def push(self, line):
        if line.strip() == '/':
            return True

        self.buffer.append(line)
        return False

    def run(self, interpreter):
        interpreter.send(self.statement())


class Interpreter:
    def __init__(self):
        self.engine = None
        self.commands = {
                'QUIT':     dict(action=self.doQuit,
                                usage="quit",
                                desc="quit the command line interpreter"),
                'CONNECT':  dict(action=self.doConnect,
                                usage="connect url",
                                desc="establish a connection to the database"),
                'HELP':     dict(action=self.doHelp,
                                usage="help [command]",
                                desc="get some help"),
        }
        self.curr = None
        self.prev = None

    def push(self, line):
        """Push a command line into the buffer.

        Will trigger execution if:
        - the line is the first line and start with a known
          command
        - the line ends with a ';' and the first line of the
          buffer starts with a known sql command
        - the line contains only '/'

        Returns 0 if the command was executed
        """
        line = line.strip()

        if not self.curr:
            # First line of a new statement
            if not line:
                return 0

            if line == '/':
                if self.prev:
                    self.prev.run(self)
                return 0

            tk = line.split()
            if tk[0].upper() in self.commands:
                self.curr = InternalCommand()
            else:
                self.curr = OtherCommand()

        if self.curr.push(line):
            self.curr.run(self)
            (self.prev, self.curr) = (self.curr, None)
            return 0
        else:
            return 1

            

    def eval(self, statement):
        args = statement.split() # XXX Maybe we should be smarter here (quotes?)

        if args: # Ignore blank lines
            cmd = self.commands[args[0].upper()]
            try:
                result = cmd['action'](statement, *args[1:])
                if result:
                    print("ok -", result)
            except ArgumentError as err:
                print("Error: command", args[0], file=sys.stderr)
                print("   ", err.args[0], file=sys.stderr)

    def doQuit(self, statement, *args):
        if len(args) > 0:
            raise ArgumentError("No argument required")

        raise EOFError

    def doHelp(self, statement, *args):
        def showCommandHelp(cmd):
            usage = self.commands[cmd].get('usage','')
            desc = self.commands[cmd].get('desc','')
            print("    {:20s} - {:s}".format(usage, desc))

        if len(args) > 1:
            raise ArgumentError("Usage: help [command]")

        if len(args) == 1:
            cmd = args[0].upper()
            if cmd in self.commands:
                showCommandHelp(cmd)
                return

        # fall back    
        for cmd in self.commands:
            showCommandHelp(cmd)

    def doConnect(self, statement, *args):
        """Establish a connection to the database

        ``url`` is assumed to be a valid sqlalchemy connection URL
        of the form ``dialect[+driver]://user:password@host/dbname[?key=value..]``

        If the password is missing, request it from the console
        """

        if len(args) != 1:
            raise ArgumentError("Usage: connect url")

        purl = re.split('(:|@)', args[0])
        #                ^^^^^
        #            is this correct?

        if len(purl) < 3 or purl[3] not in (':', '@'):
            raise ArgumentError("Can't parse URL")

        if purl[3] == '@':
            # No password
            passwd = getpass()
            purl = purl[:3] + [':', passwd] + purl[3:]

        self.engine = sqlalchemy.create_engine("".join(purl))
        return self.engine

    def send(self, statement):
        self.engine.execute(statement)
        pass
