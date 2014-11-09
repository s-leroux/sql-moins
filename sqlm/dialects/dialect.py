class Command:
    """Base class for every command
    """
    def __init__(self, action):
        self._action = action

    def do(self, statement):
        return self._action(statement)

    def filter(self, line):
        """Filter an input line to check for end-of-statement.
        """
        return (line, False)

class SQLCommand(Command):
    def filter(self, line):
        """Filter an input line to check for end-of-statement.

        For SQL, a semi-colon indicates the end-of-statement. The semi-colon
        is *not* part of the statement
        """
        line = line.rstrip()
        if line and line[-1] == ';':
            return (line[:-1], True)
        else:
            return (line, False)
    
class Dialect:
    """Base class for every dialect
    """
    def __init__(self, action):
        self._action = action

    def match(self, tokens):
        return False

