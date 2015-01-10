import re

_RD_IGNORE = re.compile(r'(\s+)|(\s*[-+=#]+\s*)')


_RD_PIPE_SEP =        re.compile(r'\s+[|]\s+')
_RD_TAB_SEP =         re.compile(r'\t+')
_RD_DOUBLESPACE_SEP = re.compile(r'\s\s+')
_RD_SPACE_SEP =       re.compile(r'\s+')
_RD_NO_SEP =          re.compile(r'')

_SEP = (
    _RD_PIPE_SEP,
    _RD_TAB_SEP,
    _RD_DOUBLESPACE_SEP,
    _RD_SPACE_SEP,
    _RD_NO_SEP,
)

_RD_NUMBER_PATTERN =          re.compile(r'^([-+]?)(\d*)[.]?(\d*)$')

class Reader:
    def parse(self, ifile):
        data = (line.strip() for line in ifile
                             if not _RD_IGNORE.match(line))

        firstLine = next(data)
        for sep in _SEP:
            columns = sep.split(firstLine)
            if len(columns) > 1:
                break

        return self.parseData(columns, data, sep)
        # the above code assume the fallback-case is the last of the list
        # raise ValueError("Can't identify the separator")

    def parseData(self, columns, data, sep):
        result = []
        for line in data:
            row = sep.split(line)

            if len(row) != len(columns):
                # fall back
                row = _RD_SPACE_SEP.split(line)

            if len(row) != len(columns):
                raise ValueError("Columns / data mismatch using " + 
                                    repr(str(sep)))

            result.append(row)

        return self.guessType(columns, result), result
       
    def guessType(self, columns, data):
        width = len(columns)
        types = [ ]

        for i in range(0, width):
            numLeft = 1;
            numRight = 0;
            strPrecision = 1;
            
            for row in data:
                val = row[i]

                if val.upper() == 'NULL':
                    continue

                if strPrecision:
                    strPrecision = max(strPrecision, len(val))

                if numLeft:
                    m = _RD_NUMBER_PATTERN.match(val)
                    l2 = len(m.group(2)) if m else 0
                    l3 = len(m.group(3)) if m else 0
                    if l2 or l3:
                        numLeft = max(numLeft, l2)
                        numRight = max(numRight, l3)
                    else:
                        numLeft = 0

            types.append(
               (columns[i], 'NUMBER', numLeft+numRight, numRight) if numLeft 
               else (columns[i], 'VARCHAR', strPrecision, 0))
                    
        return types
        

          
