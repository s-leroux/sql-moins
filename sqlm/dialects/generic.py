from sqlm.dialects.dialect import Dialect, SQLCommand

class GenericDialect(Dialect):
    def match(self, tokens):
        """Check if a list of tokens (``words'') match the current dialect.
        """
        #print("test",tokens)
        if "".join(tokens[:1]).upper() in ('INSERT', 'UPDATE',
                                         'DELETE', 'SELECT',
                                         'DROP'):
            return SQLCommand(self._action)
        elif " ".join(tokens[0:2]).upper() in ('CREATE TABLE', 'CREATE VIEW'):
            return SQLCommand(self._action)
        
        return None

