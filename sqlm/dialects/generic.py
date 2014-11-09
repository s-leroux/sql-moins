from sqlm.dialects.dialect import SQLDialect

class GenericDialect(SQLDialect):
    def match(self, tokens):
        """Check if a list of tokens (``words'') match the current dialect.
        """
        #print("test",tokens)
        if "".join(tokens[:1]).upper() in ('INSERT', 'UPDATE',
                                         'DELETE', 'SELECT',
                                         'DROP'):
            return True
        elif " ".join(tokens[0:2]).upper() in ('CREATE TABLE', 'CREATE VIEW'):
            return True
        
        return False

