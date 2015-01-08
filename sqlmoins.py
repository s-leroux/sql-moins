#!/usr/bin/python3

from sqlm.console import Console
from sqlm.interpreter import Environment
from sqlm.interpreter import Interpreter

environment = Environment()
console = Console(environment)
interpreter = Interpreter(console)
console.run(interpreter)
