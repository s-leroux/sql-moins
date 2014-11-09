from  sqlm.dialects.generic import GenericDialect
from  sqlm.dialects.dialect import SQLCommand

class OracleDialect(GenericDialect):
    def match(self, tokens):
        """Check if a list of tokens (``words'') match the current dialect.
        """
        cmd = super(OracleDialect,self).match(tokens)
        if cmd is not False:
            return cmd

        # 1 word statements
        stmt = " ".join(tokens[:1]).upper()
        if stmt in ('MERGE'):
            return SQLCommand(self._action)

        # 2 words statements
        stmt = " ".join(tokens[:2]).upper()
        if stmt in ('CREATE SEQUENCE'):
            return SQLCommand(self._action)
        elif stmt in ('CREATE'):
            return None # Undefined
        
        return False # Not an SQL statement

