import sys
import re
from getpass import getpass
import sqlalchemy
import traceback

from sqlm.formatter import TabularFormatter
from sqlm.dialects import Dialects
from sqlm.dialects.dialect import Dialect, Command

class ArgumentError(Exception):
    def __init__(self, message):
        super(ArgumentError, self).__init__(message)

class InternalCommand(Command):
    def filter(self, line):
        """Filter an input line to check for end-of-statement.

        Internal commands are one line only.
        """
        return (line, True)

class InternalDialect(Dialect):
    def __init__(self, commands, action):
        super(InternalDialect,self).__init__(action)
        self._commands = commands

    def match(self, tokens):
        """Check if a list of tokens (``words'') match the current dialect.
        """
        if "".join(tokens[:1]).upper() in self._commands:
            return InternalCommand(self._action)
        
        return None


class PLDialect(Dialect):
    """``Match all'' dialect
    """
    def match(self, tokens):
        """Check if a list of tokens (``words'') match the current dialect.
        """
        return Command(self._action)

class Statement:
    def __init__(self, dialects):
        self._statement = ""
        self._dialects = dialects
        self._command = None
        self._completed = False

    def __str__(self):
        return self._statement

    def push(self, line):
        if self._completed:
            raise ValueError("Statement {} is completed. Can't add {}".format(
                                self._statement,
                                line))

        self._command = self.findCommand(self._statement + '\n' + line)
        #print(self._dialect)

        if self._command:
            line, self._completed = self._command.filter(line)

        if self._statement:
            self._statement += '\n'
        self._statement += line

        return self._completed

    def doIt(self):
        return self._command.do(self._statement)

    def findCommand(self, statement):
        """Try to identify the dialect of the statement.

        Returns None if the dialect can't be identified.
        """
        tokens = statement[0:20].split()
        for dialect in self._dialects:
            cmd = dialect.match(tokens)
            if cmd:
                return cmd

        return None

class Environment:
    def __init__(self):
        self.errorHandlers = {
            "DEBUG":    self.reportErrorDebug,
            "NORM":     self.reportErrorNorm,
        };
        self.reportError = self.errorHandlers["NORM"]

    def setErrorLevel(self, level):
        handler = self.errorHandlers.get(level.upper())
        if handler:
            self.reportError = handler
        else:
            raise("Invalid error level: " + level)

    def reportErrorDebug(self,err):
        print(err, file=sys.stderr)
        traceback.print_tb(err.__traceback__)

    def reportErrorNorm(self, err):
        print(err, file=sys.stderr)

class Interpreter:
    def __init__(self, env):
        self.engine = None
        self.environment = env
        self.formatter = TabularFormatter()

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
                'SET':     dict(action=self.doSet,
                                usage="set param value",
                                desc="Change internal parameter"),
        }
        self.curr = None
        self.prev = None
        self._dialects = (InternalDialect(self.commands, self.eval),
                          Dialects[""](self.send),
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
                result = self.prev.doIt()
                if result:
                    self.display(result)

            return 0

        if not self.curr:
            # First line of a new statement
            if not line:
                return 0

            stmt = Statement(self._dialects)
            (self.prev, self.curr) = (self.curr, stmt)

        if self.curr.push(line):
            (self.prev, self.curr) = (self.curr, None)
            result = self.prev.doIt()
            if result:
                self.display(result)
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

    def doSet(self, statement, *args):
        if len(args) != 2:
            raise ArgumentError("2 arguments required")

        if args[0].upper() == "ERRORLEVEL":
            self.environment.setErrorLevel(args[1].upper())
        else:
            raise ArgumentError("Invalid parameter: "+args[0])
        

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

        self._dialects = (InternalDialect(self.commands, self.eval),
                          Dialects[purl[0].upper()](self.send),
                          PLDialect(self.send))

        return self.engine

    def display(self, result):
        if result.returns_rows:
            self.formatter.display(self.environment, result)
        if result.rowcount >= 0:
            print("Found",result.rowcount,"rows")

    def send(self, statement):
        statement = str(statement)
        return self.engine.execute(statement)
        
