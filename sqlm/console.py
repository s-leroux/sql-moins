import os
import sys
import atexit
import readline
import traceback

#
# from https://docs.python.org/3/library/readline.html#example
#
histfile = os.path.join(os.path.expanduser("~"), ".sqlmoins_history")
try:
    readline.read_history_file(histfile)
except FileNotFoundError:
    pass

atexit.register(readline.write_history_file, histfile)

import locale
from collections import defaultdict
#
# Infer NLS_LANG 
if 'NLS_LANG' not in os.environ:
    # According to POSIX, a program which has not called 
    # setlocale(LC_ALL, '') runs using the portable 'C' 
    # locale. Calling setlocale(LC_ALL, '') lets it use 
    # the default locale as defined by the LANG variable.
    #
    #See https://docs.python.org/3/library/locale.html#locale.getdefaultlocale
    locale.setlocale(locale.LC_ALL, '')
    country, encoding = locale.getdefaultlocale()

    encodings = defaultdict(lambda:'UTF8', {
        'UTF-8': 'UTF8'
    })

    countries = defaultdict(lambda:'FRENCH_FRANCE', {
        'fr_FR':    'FRENCH_FRANCE'
    })

    os.environ['NLS_LANG'] = "{}.{}".format(
                                        countries[country.upper()],
                                        encodings[encoding.upper()])
    print(os.environ['NLS_LANG'])

class InputStream:
    def readNextLine(self, prompt):
        raise EOFError()

class FileInputStream(InputStream):
    def __init__(self, path):
        self._file = open(path, 'rt')

    def readNextLine(self, prompt):
        line = self._file.readline()
        if not line:
            self._file.close()
            raise EOFError()

        return line

class ConsoleInputStream(InputStream):
    def readNextLine(self, prompt):
        return input(prompt)
        

class Console:
    def __init__(self):
        self._inputs = [ ConsoleInputStream() ]

        try:
            user_init = FileInputStream('sql-moins.sql')
            self.pushInputStream(user_init)
        except FileNotFoundError:
            pass

    def run(self, interpreter, env):
        while self._inputs:
            try:
                self.interact(interpreter)
            except EOFError:
                self._inputs.pop(0)
                print()
            except Exception as err:
                env.reportError(err)

    def pushInputStream(self, input_stream):
        self._inputs.insert(0, input_stream)

    def interact(self, interpreter):
        prompt = 'SQL> '
        n = 1
        try:
            while True:
                line = self._inputs[0].readNextLine(prompt)
                if interpreter.push(line) == 0:
                    break

                n += 1
                prompt = '{:3d}  '.format(n)
        except KeyboardInterrupt:
            interpreter.abort()

