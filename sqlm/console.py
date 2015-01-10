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

    def abort(self):
        """Give up using this input stream.

        Should close any ressource still allocated by this stream.
        Returns 1 if the stream is closed.
        Returns 0 if the stream cannot be closed
        """
        return 1

    def reader(self, prompt= '', eof=None):
        """
        Return an iterator that read the current
        input stream displaying the given prompt on each line
        """
        try:
            while True:
                line = self.readNextLine(prompt)
                if line != eof:
                    yield line
                else:
                    break
        except EOFError:
            pass
        

class FileInputStream(InputStream):
    def __init__(self, path):
        self._path = path
        self._linenum = 0
        self._file = open(path, 'rt')

    def readNextLine(self, prompt):
        line = self._file.readline()
        self._linenum += 1

        if not line:
            self._file.close()
            raise EOFError()

        return line

    def abort(self):
        print("Aborting",self._path,"on line",self._linenum, file=sys.stderr)
        self._file.close()
        return 1

class ConsoleInputStream(InputStream):
    def readNextLine(self, prompt):
        try:
            return input(prompt)
        except KeyboardInterrupt:
            print("^C") # echo the ^C
            raise

    def abort(self):
        # Never close interactive console
        return 0
        

class Console:
    def __init__(self, initial_env):
        self.environment = initial_env
        self.environment.input_stream = ConsoleInputStream()

        try:
            user_init = FileInputStream('sql-moins.sql')
            self.pushInputStream(user_init)
        except FileNotFoundError:
            pass

    def run(self, interpreter):

        while self.environment:
            try:
                self.interact(interpreter)
            except EOFError:
                self.environment = self.environment.pop()
                print()
            except Exception as err:
                self.environment.reportError(err)

                while self.environment.input_stream.abort():
                    self.environment = self.environment.pop()


    def pushInputStream(self, input_stream):
        self.environment = self.environment.push()
        self.environment.input_stream = input_stream

    def interact(self, interpreter):
        prompt = 'SQL> '
        n = 1
        try:
            while True:
                line = self.environment.input_stream.readNextLine(prompt)
                if interpreter.push(self.environment, line) == 0:
                    break

                n += 1
                prompt = '{:3d}  '.format(n)
        except KeyboardInterrupt:
            interpreter.abort()

