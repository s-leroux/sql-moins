import os
import sys
import re
import shlex
import subprocess
from getpass import getpass
import sqlalchemy
import traceback

from sqlm.console import FileInputStream
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
        self.push(line)
        self._completed = True
        return self


class InternalDialect(Dialect):
    """
    The internal command language

    Maps all commands to a method of the interpreter.
    """
    
    def __init__(self, commands, action):
        super(InternalDialect,self).__init__(action)
        self._commands = commands

    def match(self, tokens):
        """Check if a list of tokens match a known command
        """
        tk = "".join(tokens[:1])
        if tk[:1] == '@':
            return InternalCommand(self._action, self._commands['@'])

        tk = "".join(tokens[:1]).upper()
        cmd = self._commands.get(tk)

        if cmd:
            return InternalCommand(self._action, cmd)
        
        return False

class PLCommand(Command):
    pass

class PLDialect(Dialect):
    """``Match all'' dialect
    """
    def match(self, tokens):
        """Check if a list of tokens (``words'') match the current dialect.
        """
        return PLCommand(self._action)

class GenericCommand(Command):
    def __init__(self, dialects):
        super(GenericCommand,self).__init__(None)
        self._dialects = dialects

    def tokenize(self):
        stmt = self._statement.rstrip()

        # Remove trailing ';' for token parsing
        # AFAICT the only legal use of a semi-colon at end-of-line
        # is to end an SQL statement.
        if stmt.endswith(';'):
            stmt = stmt[:-1]

        return stmt.split()

    def filter(self, line):
        self.push(line)
        tokens = self.tokenize()
        dialects = self._dialects

        while dialects:
            dialect, *dialects = dialects
            cmd = dialect.match(tokens)
            print(dialect, cmd)
            if cmd:
                return cmd.filter(self._statement)
            elif cmd is None:
                break

        self._dialects = dialects
        return self

    def doIt(self):
        tokens = self.tokenize()
        for dialect in self.dialects:
            cmd = dialect.match(tokens)
            if cmd:
                cmd = cmd.filter(self._statement)
                return cmd.doIt()

        return None
        

class Statement:
    def __init__(self, dialects):
        self._command = GenericCommand(dialects)
        self._completed = False

    def __str__(self):
        return self._command._statement

    def push(self, line):
        if self._command._completed:
            raise ValueError("Statement {} is completed. Can't add {}".format(
                                self._statement,
                                line))

        self._command = self._command.filter(line)
        # print(self._command)
        return self._command._completed

    def doIt(self):
        return self._command.doIt()

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
    def __init__(self, console, env):
        self.engine = None
        self.console = console
        self.environment = env
        self.formatter = TabularFormatter()

        self.commands = {
                '@':     dict(action=self.doRunScript,
                                usage="@path",
                                desc="execute the commands from a script"),
                'HISTORY':     dict(action=self.doHistory,
                                usage="history",
                                desc="Show the last commands stored into the buffer"),
                'ED':     dict(action=self.doEdit,
                                usage="ed path",
                                desc="launch a text $EDITOR"),
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
        self.history = []
        self.curr = None
        self.prev = None
        self._dialects = (InternalDialect(self.commands, self.eval),
                          Dialects[""](self.send),
                          PLDialect(self.send))

    def shiftBuffer(self, new_value = None):
        """
        Push a new value in the buffer history
        """
        if self.prev is not None:
            self.history.append(self.prev)

        (self.prev, self.curr) = (self.curr, new_value)

    def abort(self):
        """Abort the current statement.

        If the current statement is not empty, push in
        onto the stack immediately without executing it.

        If the current statement is empty or blank, do nothing.
        """
        if self.curr is not None and str(self.curr).strip():
            self.shiftBuffer()



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
                self.shiftBuffer()

            if self.prev:
                self.prev.doIt()

            return 0

        if not self.curr:
            # First line of a new statement
            if not line:
                return 0

            stmt = Statement(self._dialects)
            self.shiftBuffer(stmt)

        if self.curr.push(line):
            self.shiftBuffer()
            self.prev.doIt()
            return 0
        else:
            return 1

    def eval(self, statement, cmd):
        statement = str(statement)
        args = shlex.split(statement)
        print(args)

        if args: # Ignore blank lines
            try:
                result = cmd['action'](statement, *args[1:])
                if result:
                    print("ok -", result)
            except ArgumentError as err:
                print("Error: command", args[0], file=sys.stderr)
                print("   ", err.args[0], file=sys.stderr)

    #def getArgs(self, n, args):
    #    return self.getArgs(n,n,args)

    def getArgs(self, min, max, args):
        if not (min <= len(args) <= max):
            msg = str(min) + " to " + str(max) if min != max else str(min)
            raise ArgumentError(msg + " required arguments")

        return (args + (None,)*(max-min))[:max]

    def doRunScript(self, statement, *args):
        script = statement[1:].strip()
        print("Running:", script)
        input_stream = FileInputStream(script)
        self.console.pushInputStream(input_stream)

    def doEdit(self, statement, *args):
        """
        Launch an editor.

        Without any argument, edit the last command in the buffer
        in the file 'edbuf.sql'

        With a number as argument, do the same as above, but
        using the n-th value of the buffer

        Otherwise, edit the given file
        """
        (path,) = self.getArgs(0, 1, args)

        if not path:
            # Edit the buffer in a special file
            path = 'edbuf.sql'
            with open(path, 'wt') as f:
                f.write(str(self.history[-1]))
                f.write('\n/\n')

        elif re.match('^[0-9]+$', path):
            n = int(path)
            path = 'edbuf.sql'
            with open(path, 'wt') as f:
                f.write(str(self.history[n]))
                f.write('\n/\n')
            

        editor = os.environ.get('EDITOR')
        if not editor:
            editor = 'vi'

        print("Editing:", path, "with", editor)
        subprocess.call([editor, path])

    def doHistory(self, statement, *args):
        self.getArgs(0, 0, args)

        for idx, val in enumerate(self.history):
            header = "{:4d}".format(idx)
            for line in str(val).splitlines():
                print("{}  {}".format(header,line))
                header = "    "

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

    def display(self, result, tagline = None):
        if result.returns_rows:
            self.formatter.display(self.environment, result)

        rowcount = result.rowcount
        if tagline and rowcount >= 0:
            print(tagline.format(n=rowcount,
                                 rows="rows" if rowcount > 1 else "row"))

    def send(self, statement, tagline = None):
        statement = str(statement)
        result = self.engine.execute(statement)
        if result:
            self.display(result, tagline)
        
