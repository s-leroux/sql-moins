class Interpreter:
    def eval(self, statement):
        if statement.strip().upper() == 'QUIT':
            raise EOFError;
        pass
