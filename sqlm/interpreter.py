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

class SQLCommand(Command):
    def push(self, line):
        isLast = False
        line = line.rstrip()
        if line.endswith(';'):
            line = line[:-1].rstrip()
            isLast = True

        self.buffer.append(line)
        return isLast

    def run(self, interpreter):
        interpreter.send(self.statement())

class OtherCommand(Command):
    def push(self, line):
        if line.strip() == '/':
            return True

        self.buffer.append(line)
        return False

    def run(self, interpreter):
        interpreter.send(self.statement())

class SQLDialect:
    def __init__(self, action):
        self._action = action

    def match(self, tokens):
        """Check if a list of tokens (``words'') match the current dialect.
        """
        #print("test",tokens)
        if "".join(tokens[:1]).upper() in ('INSERT', 'UPDATE', 'MERGE', 
                                         'DELETE', 'SELECT',
                                         'DROP'):
            return True
        elif " ".join(tokens[0:2]).upper() in ('CREATE TABLE', 'CREATE VIEW'):
            return True
        
        return False

    def do(self, statement):
        self._action(statement)

    def filter(self, line):
        """Filter an input line to check for end-of-statement.

        For SQL, a semi-colon indicates the end-of-statement. The semi-colon
        should be removed from the statement
        """
        line = line.rstrip()
        if line and line[-1] == ';':
            return (line[:-1], True)
        else:
            return (line, False)

class InternalDialect:
    def __init__(self, action):
        self._action = action

    def match(self, tokens):
        """Check if a list of tokens (``words'') match the current dialect.
        """
        if "".join(tokens[:1]).upper() in ('QUIT','CONNECT','HELP'):
            return True
        
        return False

    def do(self, statement):
        self._action(statement)

    def filter(self, line):
        """Filter an input line to check for end-of-statement.

        Internal commands are one line only.
        """
        return (line, True)

class PLDialect:
    def __init__(self, action):
        self._action = action

    def match(self, tokens):
        """Check if a list of tokens (``words'') match the current dialect.
        """
        return True

    def do(self, statement):
        self._action(statement)

    def filter(self, line):
        if line.strip() == '/':
            return ("", True)
        else:
            return (line, False)


class Statement:
    def __init__(self, dialects):
        self._statement = ""
        self._dialects = dialects
        self._dialect = None
        self._completed = False

    def __str__(self):
        return self._statement

    def push(self, line):
        if self._completed:
            raise ValueError("Statement {} is completed. Can't add {}".format(
                                self._statement,
                                line))

        self._dialect = self.findDialect(self._statement + '\n' + line)
        print(self._dialect)

        if self._dialect:
            line, self._completed = self._dialect.filter(line)

        if self._statement:
            self._statement += '\n'
        self._statement += line

        return self._completed

    def doIt(self):
        self._dialect.do(self._statement)

    def findDialect(self, statement):
        """Try to identify the dialect of the statement.

        Returns None if the dialect can't be identified.
        """
        tokens = statement[0:20].split()
        for dialect in self._dialects:
            if dialect.match(tokens):
                return dialect

        return None


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
        self._dialects = (InternalDialect(self.eval),
                          SQLDialect(self.send),
                          PLDialect(self.send))


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
        line = line.rstrip()

        if line.strip() == '/':
            # special case: if there is a pending command, terminate it
            # and execute
            if self.curr:
                (self.prev, self.curr) = (self.curr, None)

            if self.prev:
                self.send(self.prev)

            return 0

        if not self.curr:
            # First line of a new statement
            if not line:
                return 0

            stmt = Statement(self._dialects)
            (self.prev, self.curr) = (self.curr, stmt)

        if self.curr.push(line):
            (self.prev, self.curr) = (self.curr, None)
            self.prev.doIt()
            return 0
        else:
            return 1

    def eval(self, statement):
        statement = str(statement)
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
        statement = str(statement)
        self.engine.execute(statement)
        pass
