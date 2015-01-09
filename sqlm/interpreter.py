import os
import sys
import re
import shlex
import subprocess
from getpass import getpass
from copy import copy
import sqlalchemy
import traceback

from sqlm.dialects.oracle import OracleDialect
from sqlm.tabular import Reader
from sqlm.console import FileInputStream
from sqlm.formatter import TabularFormatter
from sqlm.utils import numSelector

class ArgumentError(Exception):
    def __init__(self, message):
        super(ArgumentError, self).__init__(message)

class Environment:
    def __init__(self):
        self.next = None # for linked list of environments

        self.errorHandlers = {
            "DEBUG":    self.reportErrorDebug,
            "NORM":     self.reportErrorNorm,
        };
        self.errorLevel = "NORM"
        self.reportError = self.errorHandlers[self.errorLevel]

        self.terminations = {
            ";":        re.compile(r'^(.*);$', re.DOTALL),
            "/":        re.compile(r'^(.*)\n/$', re.DOTALL)
        }
        self.termination = self.terminations[";"]

    def push(self):
        c = copy(self)
        c.next = self
        return c

    def pop(self):
        return self.next

    def __setitem__(self, i, v):
        if i == "ERRORLEVEL":
            self.setErrorLevel(v.upper())
        elif i == "TERMINATION":
            self.setTermination(v.upper())
        else:
            raise ArgumentError("Unknown parameter " + i)

    def setErrorLevel(self, level):
        handler = self.errorHandlers.get(level.upper())
        if handler:
            self.reportError = handler
        else:
            raise("Invalid error level: " + level)

    def setTermination(self, term):
        self.termination = self.terminations[term]

    def reportErrorDebug(self,err):
        print(err, file=sys.stderr)
        traceback.print_tb(err.__traceback__)

    def reportErrorNorm(self, err):
        print(err, file=sys.stderr)

class Command:
    def __init__(self, action = None, desc = "", usage = "" , args = ()):
        self.action = action
        self.desc = desc
        self.usage = usage
        self.args = args

    def doIt(self, env):
        try:
            return self.action(env, *self.args)
        except ArgumentError as err:
            print("Error:", self.desc)
            print(self.usage)
            raise
    

class Interpreter:
    """
    The Interpreter.

    This object is responsible to assembly lines into statements.
    If the first line of a statement start with a known internal
    command it will be executed immediatly. Otherwise, a statement
    is assembled and send to the server when the termination pattern
    is detected.
    """
    def __init__(self, console):
        self.engine = None
        self.connection = None
        self.console = console
        self.formatter = TabularFormatter()

        self.commands = {
                '!':     dict(action=self.doRunPrevious,
                                usage="!num",
                                desc="execute a command from the buffer history"),
                '@':     dict(action=self.doRunScript,
                                usage="@path",
                                desc="execute the commands from a script"),
                'HISTORY':     dict(action=self.doHistory,
                                usage="history",
                                desc="Show the last commands stored into the buffer"),
                'READ':     dict(action=self.doRead,
                                usage="read table_name",
                                desc="Read tabular data to create a table"),
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
        self.curr = "" # The current statement as a list of lines

    def findCommand(self, stmt):
        args = shlex.split(stmt)
        if args and args[0]:
            cmd = self.commands.get(args[0].upper())
            if not cmd:
                cmd = self.commands.get(args[0][0])
                if cmd:
                    args = (args[0][0], args[0][1:].strip()) + tuple(args[1:])

        if cmd:
            return Command(args=args[1:], **cmd);

        return None

    def abort(self):
        """Abort the current statement.

        If the current statement is not empty, push in
        onto the stack immediately without executing it.

        If the current statement is empty or blank, do nothing.
        """
        if self.curr.strip():
            self.history.append(self.curr)
            self.curr = ""

    def push(self, env, line):
        """Push a command line into the buffer.

        Will trigger execution if:
        - the line is the first line and start with a known
          command
        - the line ends with a ';' and the first line of the
          buffer starts with a known sql command
        - the line contains only '/'

        Returns 0 if the command was executed
        """

        # Remove trailing spaces
        line = line.rstrip()

        if not self.curr:
            # First line of a new statement
            if not line:
                return 0

            cmd = self.findCommand(line)
            if cmd:
                cmd.doIt(env)
                self.curr = ""
                return 0

        execute = False
        # Special case
        if line == '/':
            if self.curr:
                self.history.append(self.curr)
                self.curr = ""

            execute = True

        else:

            # Not the first line, or not an internal command
            # add to the buffer and test for termination
            self.curr = line if not self.curr else "\n".join((self.curr, line))

            match = env.termination.match(self.curr)

            if match:
                stmt = match.group(1)

                # push non empty statement onto the stack
                if stmt.strip():
                    self.history.append(stmt)

                self.curr = ""
                execute = True


        if execute:
            self.send(env, self.history[-1])

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

    def doRunPrevious(self, env, *expr):
        for num in numSelector(expr):
            self.send(env, self.history[num])

    def doRunScript(self, env, script):
        print("Running:", script)
        input_stream = FileInputStream(script)
        self.console.pushInputStream(input_stream)

    def doRead(self, env, tbl):
        r = Reader()
        columns, rows = r.parse(sys.stdin)

        self.history.append(self.dialect.makeCreateTable(tbl, columns, rows))
        self.history.append(self.dialect.makeInserts(tbl, columns, rows))

    def doEdit(self, env, *args):
        """
        Launch an editor.

        Usage:
            ed [filename]? [n|n1-n2]*

        Without any argument, edit the last command in the buffer
        in the file 'edbuf.sql'

        With a number as argument, do the same as above, but
        using the n-th value of the buffer

        Otherwise, edit the given file
        """

        # Set default values
        path = 'edbuf.sql'
        sel = (-1,)

        if len(args):
            if re.match(r"^[-+]?\d+(-[-+]?\d+)?$", args[0]):
                sel = args
            else:
                path = args[0]
                sel = args[1:] or (-1,)

        with open(path, 'wt') as f:
            for n in numSelector(sel):
                f.write(str(self.history[n]))
                f.write('\n/\n')

        editor = os.environ.get('EDITOR')
        if not editor:
            editor = 'vi'

        print("Editing:", path, "with", editor)
        subprocess.call([editor, path])

    def doHistory(self, env):
        for idx, val in enumerate(self.history):
            header = "{:4d}".format(idx)
            for line in str(val).splitlines():
                print("{}  {}".format(header,line))
                header = "    "

    def doQuit(self, env):
        raise EOFError

    def doHelp(self, env, *args):
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

    def doSet(self, env, attr, value):
        self.environment[attr.upper()] = value

    def doConnect(self, env, url):
        """Establish a connection to the database

        ``url`` is assumed to be a valid sqlalchemy connection URL
        of the form ``dialect[+driver]://user:password@host/dbname[?key=value..]``

        If the password is missing, request it from the console
        """
        purl = re.split('(:|@)', url)
        #                ^^^^^
        #            is this correct?

        if len(purl) < 3 or purl[3] not in (':', '@'):
            raise ArgumentError("Can't parse URL")

        if purl[3] == '@':
            # No password
            passwd = getpass()
            purl = purl[:3] + [':', passwd] + purl[3:]

        the_engine = sqlalchemy.create_engine("".join(purl))
        the_connection = the_engine.connect()

        # new connection OK: update the member data
        self.dialect_name = re.split(r'[+:]', url, 1)[0]
        if self.dialect_name == 'oracle':
            self.dialect = OracleDialect()
        else:
            self.dialect = OracleDialect() # XXX Should use Generic Dialect

        self.engine = the_engine
        self.connection = the_connection


        if not self.connection:
            raise ArgumentError("Can't connect (wrong password?)")

        return self.connection

    def display(self, env, result, tagline = None):
        if result.returns_rows:
            self.formatter.display(env, result)

        rowcount = result.rowcount
        if tagline and rowcount >= 0:
            print(tagline.format(n=rowcount,
                                 rows="rows" if rowcount > 1 else "row"))

    def send(self, env, statement, tagline = "\n{n:d} {rows}.\n"):
        statement = str(statement)
        result = self.connection.execute(statement)
        if result:
            self.display(env, result, tagline)
        
