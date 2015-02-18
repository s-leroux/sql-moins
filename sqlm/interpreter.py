import os
import sys
import re
import shlex
import subprocess
from getpass import getpass
from copy import copy
import traceback

from sqlm.dialects.oracle import OracleDialect
from sqlm.tabular import Reader
from sqlm.console import FileInputStream
from sqlm.formatter import TabularFormatter
from sqlm.utils import numSelector

import sqlm.parser
import sqlm.utils
import sqlm.engine

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
        self.bindvar = {}

        self.autocommit = True

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
        elif i == "AUTOCOMMIT":
            if v.upper() in ("TRUE", "ON", "1"):
                self.autocommit = True
            elif v.upper() in ("FALSE", "OFF", "0"):
                self.autocommit = False
            else:
                raise ArgumentError("Not a valid option for AUTOCOMMIT " + v)
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
        print(err.__class__.__name__ + ":", err, file=sys.stderr)
        traceback.print_tb(err.__traceback__)

    def reportErrorNorm(self, err):
        print(err.__class__.__name__ + ":", err, file=sys.stderr)

    def bind(self, var, typ, value=None):
        self.bindvar[var.upper()] = (typ, value)

    def bound(self, var):
        return self.bindvar[var.upper()]

    def update(self, var, value):
        typ, _ = self.bindvar[var.upper()]
        self.bindvar[var.upper()] = (typ, value)

        

class Command:
    def __init__(self, action = None, pattern=(), desc = "", usage = "" , args = (), kw = {}):
        self.action = action
        self.desc = desc
        self.usage = usage
        self.args = args
        self.pattern = pattern
        self.kw = kw

    def doIt(self, env):
        try:
            return self.action(env, *self.args, **self.kw)
        except ArgumentError as err:
            print("Error:", self.desc)
            print(" ".join(self.pattern))
            print(self.usage)
            raise
    

class Interpreter:
    """
    The Interpreter.

    This object is responsible to merge lines into statements.
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

        self.ncommands = {
            "!" : dict(
                usage="!events...",
                action=self.doRunPrevious,
                desc="execute a command from the buffer history",
            ),
            "@" : dict(
                usage="@path",
                action=self.doRunScript,
                desc="execute the commands from a script",
            ),
            "READ" : dict(
                usage="READ tbl [ < path ] [ << heredoc ]",
                action=self.doRead,
                desc="Read tabular data to create a table",
            ),
            "SET" : dict(
                usage="SET param value",
                action=self.doSet,
                desc="Change internal parameter",
            ),
            "ED" : dict(
                usage="ED [filename] [ ! events...]",
                action=self.doEdit,
                desc="Edit some events in a file",
            ),
            "HISTORY" : dict(
                usage="HISTORY [num]",
                action=self.doHistory,
                desc="Show the last commands stored into the buffer",
            ),
            "HELP" : dict(
                usage="HELP [cmd]",
                action=self.doHelp,
                desc="get some help",
            ),
            "QUIT" : dict(
                usage="QUIT",
                action=self.doQuit,
                desc="quit the command line interpreter",
            ),
            "CONNECT" : dict(
                usage="CONNECT url",
                action=self.doConnect,
                desc="establish a connection to the database",
            ),
            "VAR" : dict(
                usage="VAR var typ",
                action=self.doVar,
                desc="Declare a bind variable",
            ),
        }

        # Compile commands patterns
        for cmd in self.ncommands.values():
            cmd['pattern'] = sqlm.parser.compile(cmd['usage'])

        self.history = []
        self.curr = "" # The current statement as a list of lines

    def findCommand(self, stmt):
        # New command parsing
        cmdline = sqlm.parser.tokenize(stmt)
        for cmd in self.ncommands.values(): # This could be optimized
                                            # using the first token as a key
            m = cmd['pattern'].match(cmdline)
            if m is not None:
                return Command(kw=m, **cmd)

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

            # Ignore empty lines or comment-only lines
            if not line or line.lstrip().startswith('--'):
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

    def doRunPrevious(self, env, events=()):
        for num in numSelector(events):
            self.send(env, self.history[num])

    def doRunScript(self, env, path=None):
        print("Running:", path)
        input_stream = FileInputStream(path)
        self.console.pushInputStream(input_stream)

    def doRead(self, env, tbl=None, path=None, heredoc='.'):
        try:
            src = None
            if path:
                src = open(path, "rt")

            r = Reader()
            columns, rows = r.parse(src if src
                                    else env.input_stream.reader('> ', heredoc))
        finally:
            if src:
                src.close()

        self.history.append(self.dialect.makeCreateTable(tbl, columns, rows))
        self.history.append(self.dialect.makeInserts(tbl, columns, rows))

        self.doHistory(env, 2)

    def doEdit(self, env, filename=None, events=()):
        """
        Launch an editor.

        Usage:
            ed [filename]? [ for [n|n1-n2]* ]?

        Without any argument, edit the last command in the buffer
        in the file 'edbuf.sql'

        With a filename, edit the given file

        With at least one buffer index, *overwrite* the content
        of the file with the given entries in the history buffer.
        """

        if filename is None:
            if not events:
                events = ("-1",)
            filename = 'edbuf.sql'

        # OVERWRITE the content of the file with the specified events
        if events:
            sel = list(numSelector(events)) # materilize the list first
                                          # to avoid partial overwrite
                                          # of the file in case of
                                          # incorrectly formated arguments
            with open(filename, 'wt') as f:
                for n in sel:
                    f.write(str(self.history[n]))
                    f.write('\n/\n')

        editor = os.environ.get('EDITOR')
        if not editor:
            editor = 'vi'

        print("Editing:", filename, "with", editor)
        subprocess.call([editor, filename])

    def doHistory(self, env, num=0):
        if num:
            num = int(num)
            if num < 0:
                raise ArgumentError("Expected a non nul positive integer")
        else:
            num = len(self.history)

        base_idx = max(len(self.history)-num,0)
        for idx, val in enumerate(self.history[base_idx:]):
            header = "{:4d}".format(idx+base_idx)
            for line in str(val).splitlines():
                print("{}  {}".format(header,line))
                header = "    "

    def doQuit(self, env):
        raise EOFError

    def doHelp(self, env, cmd=None):
        def showNCommandHelp(cmd):
            usage = self.ncommands[cmd].get('usage','')
            desc = self.ncommands[cmd].get('desc','')
            print("    {:20s} - {:s}".format(usage, desc))

        if cmd:
            cmd = cmd.upper()
            if cmd in self.ncommands:
                showNCommandHelp(cmd)
                return

        # fall back    
        for cmd in sorted(self.ncommands.keys()):
            showNCommandHelp(cmd)

    def doSet(self, env, param=None, value=None):
        env[param.upper()] = value

    def doVar(self, env, var=None, typ=None):
        env.bind(var,typ)

    def doConnect(self, env, url=None):
        """Establish a connection to the database

        ``url`` is assumed to be of the form
        ``dialect://user:password/connection_string``

        If the password part is missing, request it from the console
        Note: this is different from the empty password!
        """
        params = sqlm.engine.parse_url(url)
        if params['password'] == None:
            # No password
            params['password'] = getpass()
        
        the_engine = sqlm.engine.Engine(params)

        self.engine = the_engine
        self.dialect = self.engine.dialect

        return self.engine

    def display(self, env, result, tagline = None):
        if result.returns_rows:
            self.formatter.display(env, result)

        rowcount = result.rowcount
        if tagline and rowcount >= 0:
            print(tagline.format(n=rowcount,
                                 rows="rows" if rowcount > 1 else "row"))

    def send(self, env, statement, tagline = "\n{n:d} {rows}.\n"):
        statement = str(statement)
        statement = self.engine.prepare(statement)

        for paramname in statement.bindnames:
            # bind parameters
            datatype, value = env.bound(paramname)
            statement.bind(paramname, datatype, value)

        result = statement.execute()
        if result:
            self.display(env, result, tagline)

        
        for paramname in statement.bindnames:
            # Get back parameter values and store them
            # in the environment
            env.update(paramname, statement[paramname])
            print(paramname, '=', statement[paramname])
        
