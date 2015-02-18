from sqlm.dialects.oracle import OracleDialect
from sqlm.dialects.sqlite import SQLiteDialect

import re

_C_URL = re.compile(r"""(\w+)://([^:/]+)?(?:(:.*))?/(.*)""")

def parse_url(url):
    m = _C_URL.fullmatch(url)
    if not m:
        return None

    dialect, username, password, db = m.groups()

    return dict(dialect=dialect,
                username=username,
                password=password[1:] if password else None,
                db=db,
    )

_DIALECTS = {
    'oracle': OracleDialect,
    'sqlite': SQLiteDialect,
}

class Engine:
    """Simple SQL engine.

    Wrapper arround the dialect object
    """

    def __init__(self, params):
        if type(params) == str:
            params = parse_url(url)

        self.dialect = _DIALECTS[params['dialect']]()
        self.conn = self.dialect.connect(**params)


    def prepare(self, stmt):
        return self.dialect.prepare(self.conn, stmt)
