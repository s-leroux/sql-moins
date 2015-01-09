class OracleDialect:
    def makeCreateTable(self, tbl, columns, rows):
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
