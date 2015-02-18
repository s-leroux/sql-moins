import sqlite3

import sqlm.resultset

class Statement:
    def __init__(self, connection, stmt):
        cursor = connection.cursor()

        self.bindnames = []
        self.bindparams = {}

        self.cursor = cursor
        self.stmt = stmt

    def __getitem__(self, bindname):
        # let it fail as this is *not* supported on SQLite
        return self.cursor.bindparams[bindname.upper()].getvalue()

    def execute(self, **bindparams):
        for var, value in bindparams.items():
            self.bindparams[var.upper()] = value

        self.cursor.execute(self.stmt, self.bindparams)

        return sqlm.resultset.ResultSet(self.cursor)

class SQLiteDialect:
    """Abstraction layer arround the SQLite3 driver.
    """

    driver = "sqlite3"

    # ------------------------------------------------------------------
    # Cursor-related abstraction layer
    # ------------------------------------------------------------------
    def prepare(self, connection, stmt):
        """Prepare a statement.

        Returns a Statement instance suitable
        to execute the statement.
        """
        return Statement(connection, stmt)

    def connect(self, db=None, **kwargs):
        return sqlite3.connect(db)

    

    # ------------------------------------------------------------------
    # Statements builder functions
    # ------------------------------------------------------------------

    def makeCreateTable(self, tbl, columns, rows):
        """Generate a `CREATE TABLE` statement"""

        lines = []
        lines.append('CREATE TABLE "{}" ('.format(tbl))

        m = []
        for name, typ, prec, scale in columns:
            if scale:
                prec = '({},{})'.format(prec,scale)
            elif prec:
                prec = '({})'.format(prec)
            else:
                prec=''

            m.append('    "{}" {}{}'.format(name, typ, prec))
        
        lines.append(",\n".join(m))
        lines.append(")")

        return "\n".join(lines)

    def makeInserts(self, tbl, columns, rows):
        """Generate a multi-rows `INSERT` statement"""

        lines = []
        lines.append("INSERT ALL")

        stmt = '    INTO "{}" ({})'.format(
                tbl,
                ", ".join(['"'+name+'"' for name, *_ in columns])
            )

        fmt = '          VALUES ({})'.format(
                ", ".join(["{}" if t in ('NUMBER') else "'{}'" 
                                for n, t, *_ in columns])
            )

        print(stmt)
        print(fmt)

        for row in rows:
            lines.append(stmt)
            lines.append(fmt.format(*row))
            

        lines.append("SELECT * FROM DUAL")

        return "\n".join(lines)
        
