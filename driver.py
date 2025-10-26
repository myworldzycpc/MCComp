import sys
from antlr4 import *
from gen.MCCDPLexer import MCCDPLexer
from gen.MCCDPParser import MCCDPParser
from ListenerInterp import ListenerInterp

def main(argv):
    input_stream = FileStream("test/test.mccdp")
    lexer = MCCDPLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = MCCDPParser(stream)
    tree = parser.start_()
    if parser.getNumberOfSyntaxErrors() > 0:
        print("syntax errors")
    else:
        listener_interp = ListenerInterp()
        walker = ParseTreeWalker()
        walker.walk(listener_interp, tree)

if __name__ == '__main__':
    main(sys.argv)