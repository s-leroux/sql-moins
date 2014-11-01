import sys
import re
from getpass import getpass
import sqlalchemy

class ArgumentError(Exception):
    def __init__(self, message):
        super(ArgumentError, self).__init__(message)

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

    def eval(self, statement):
        args = statement.split() # XXX Maybe we should be smarter here (quotes?)

        if args: # Ignore blank lines
            cmd = self.commands.get(args[0].upper(), dict(action=self.doDefault))
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

    def doDefault(self, statement, *args):
        self.engine.execute(statement)
        pass
