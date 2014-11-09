from  sqlm.dialects.dialect import Dialect, SQLCommand

class GenericDialect(Dialect):
    def match(self, tokens):
        """Check if a list of tokens (``words'') match the current dialect.
        """
        #print("test",tokens)

        # 1 word statements
        stmt = " ".join(tokens[:1]).upper()
        if stmt in ('INSERT', 'UPDATE',
                    'DELETE', 'SELECT',
                    'DROP'):
            return SQLCommand(self._action)

        # 2 words statements
        stmt = " ".join(tokens[:2]).upper()
        if stmt in ('CREATE TABLE', 'CREATE VIEW'):
            return SQLCommand(self._action)
        elif stmt in ('CREATE'):
            return None # Undefined
        
        return False # Not an SQL statement

