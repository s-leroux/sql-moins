class Command:
    """Base class for every command
    """
    def __init__(self, action, *params):
        self._action = action
        self._params = params
        self._statement = ""
        self._completed = False

    def doIt(self):
        return self._action(self._statement, *self._params)

    def push(self, line):
        if self._statement:
            self._statement += '\n'
        self._statement += line

    def filter(self, line):
        """Filter an input line to check for end-of-statement.
        """
        self.push(line)
        return self

class SQLCommand(Command):
    def filter(self, line):
        """Filter an input line to check for end-of-statement.

        For SQL, a semi-colon indicates the end-of-statement. The semi-colon
        is *not* part of the statement
        """
        line = line.rstrip()
        if line.endswith(';'):
            line = line[:-1];
            self._completed = True

        self.push(line)
        return self;
    
class Dialect:
    """Base class for every dialect
    """
    def __init__(self, action):
        self._action = action

    def match(self, tokens):
        return False


