from collections import defaultdict
from sqlm.dialects.oracle import OracleDialect
from sqlm.dialects.generic import GenericDialect

Dialects = defaultdict(lambda : GenericDialect,
                        ORACLE=OracleDialect)
