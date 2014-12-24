#!/usr/bin/python3

from sqlm.console import Console
from sqlm.interpreter import Environment
from sqlm.interpreter import Interpreter

environment = Environment()
console = Console()
interpreter = Interpreter(console, environment)
console.run(interpreter, environment)
