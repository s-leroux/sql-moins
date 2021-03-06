import cx_Oracle

import sqlm.resultset

_TYPES = {
    'BINARY' : cx_Oracle.BINARY,
    'BFILE' : cx_Oracle.BFILE,
    'BLOB' : cx_Oracle.BLOB,
    'CLOB' : cx_Oracle.CLOB,
    'CURSOR' : cx_Oracle.CURSOR,
    'DATETIME' : cx_Oracle.DATETIME,
    'CHAR' : cx_Oracle.FIXED_CHAR,
#    'NCHAR' : cx_Oracle.FIXED_UNICODE,
    'INTERVAL' : cx_Oracle.INTERVAL,
    'LOB' : cx_Oracle.LOB,
    'LONG RAW' : cx_Oracle.LONG_BINARY,
    'LONG' : cx_Oracle.LONG_STRING,
    'CLOB' : cx_Oracle.CLOB,
    'BINARY FLOAT' : cx_Oracle.NATIVE_FLOAT,
    'BINARY DOUBLE' : cx_Oracle.NATIVE_FLOAT,
    'NCLOB' : cx_Oracle.NCLOB,
    'NUMBER' : cx_Oracle.NUMBER,
    'OBJECT' : cx_Oracle.OBJECT,
    'ROWID' : cx_Oracle.ROWID,
    'VARCHAR2' : cx_Oracle.STRING,
    'TIMESTAMP' : cx_Oracle.TIMESTAMP,
#    'NVARCHAR2' : cx_Oracle.UNICODE,
}

class Statement:
    def __init__(self, connection, stmt):
        cursor = connection.cursor()
        cursor.prepare(stmt)

        self.bindnames = cursor.bindnames()
        self.bindparams = {}

        self.cursor = cursor
        self.stmt = stmt

    def __getitem__(self, bindname):
        return self.bindparams[bindname.upper()].getvalue()

    def bind(self, bindname, sqltype, value=None):
        """Bind a variable of the given type with the
        current statement.

        Variables objects values can be queried to retrieve
        OUT param values.
        """
        datatype = _TYPES[sqltype.upper()]
        var = self.cursor.var(datatype)

        if value is not None:
            var.setvalue(0,value)

        self.bindparams[bindname.upper()] = var

    def execute(self, **bindparams):
        for var, value in bindparams.items():
            self.bindparams[var.upper()] = value

        self.cursor.execute(self.stmt, self.bindparams)

        return sqlm.resultset.ResultSet(self.cursor)

class OracleDialect:
    """Abstraction layer arround the Oracle driver.
    """

    driver = "cx_Oracle"

    # ------------------------------------------------------------------
    # Cursor-related abstraction layer
    # ------------------------------------------------------------------
    def prepare(self, connection, stmt):
        """Prepare a statement.

        Returns a Statement instance suitable
        to execute the statement.
        """
        return Statement(connection, stmt)

    def connect(self, username=None, password=None, db=None, **kwargs):
        return cx_Oracle.connect(username,password,db)
    

    # ------------------------------------------------------------------
    # Statements builder functions
    # ------------------------------------------------------------------

    def makeCreateTable(self, tbl, columns, rows):
        """Generate a `CREATE TABLE` statement"""

        lines = []
        lines.append('CREATE TABLE "{}" ('.format(tbl))

        m = []
        for name, typ, prec, scale in columns:
            if typ == 'VARCHAR':
                typ = 'VARCHAR2'

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
        
