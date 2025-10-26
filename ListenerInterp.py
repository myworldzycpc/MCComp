import sys
from antlr4 import *
from gen.MCCDPParser import MCCDPParser
from gen.MCCDPListener import MCCDPListener
from bidict import bidict


class ListenerInterp(MCCDPListener):
    def __init__(self):
        self.result = {}
        self.intermediate = {}
        self.commands = []
        self.current_id = 0
        self.namespace = "mydp"

    def exitAtom(self, ctx: MCCDPParser.AtomContext):
        self.result[ctx] = int(ctx.getText())

    def exitExpr(self, ctx: MCCDPParser.ExprContext):
        print(ctx.getText())
        self.intermediate[ctx] = self.current_id
        self.current_id += 1
        if ctx.getChildCount() == 3:
            if ctx.getChild(0).getText() == "(":
                self.result[ctx] = self.result[ctx.getChild(1)]
            else:
                opc = ctx.getChild(1).getText()
                v1 = self.result[ctx.getChild(0)]
                v2 = self.result[ctx.getChild(2)]
                self.commands.append(f"scoreboard players operation __intermediate_{self.intermediate[ctx]} __{self.namespace}_global = __intermediate_{self.intermediate[ctx.getChild(0)]} __{self.namespace}_global")
                if opc == "+":
                    self.result[ctx] = v1 + v2
                    self.commands.append(f"scoreboard players operation __intermediate_{self.intermediate[ctx]} __{self.namespace}_global += __intermediate_{self.intermediate[ctx.getChild(2)]} __{self.namespace}_global")
                elif opc == "-":
                    self.result[ctx] = v1 - v2
                    self.commands.append(f"scoreboard players operation __intermediate_{self.intermediate[ctx]} __{self.namespace}_global -= __intermediate_{self.intermediate[ctx.getChild(2)]} __{self.namespace}_global")
                elif opc == "*":
                    self.result[ctx] = v1 * v2
                    self.commands.append(f"scoreboard players operation __intermediate_{self.intermediate[ctx]} __{self.namespace}_global *= __intermediate_{self.intermediate[ctx.getChild(2)]} __{self.namespace}_global")
                elif opc == "/":
                    self.result[ctx] = v1 / v2
                    self.commands.append(f"scoreboard players operation __intermediate_{self.intermediate[ctx]} __{self.namespace}_global /= __intermediate_{self.intermediate[ctx.getChild(2)]} __{self.namespace}_global")
                elif opc == "%":
                    self.result[ctx] = v1 % v2
                    self.commands.append(f"scoreboard players operation __intermediate_{self.intermediate[ctx]} __{self.namespace}_global %= __intermediate_{self.intermediate[ctx.getChild(2)]} __{self.namespace}_global")
                else:
                    self.result[ctx] = 0
        elif ctx.getChildCount() == 2:
            opc = ctx.getChild(0).getText()
            if opc == "+":
                v = self.result[ctx.getChild(1)]
                self.result[ctx] = v
                self.commands.append(f"scoreboard players operation __intermediate_{self.intermediate[ctx]} __{self.namespace}_global = __intermediate_{self.intermediate[ctx.getChild(1)]} __{self.namespace}_global")
            elif opc == "-":
                v = self.result[ctx.getChild(1)]
                self.result[ctx] = - v
                self.commands.append(f"scoreboard players set __intermediate_{self.intermediate[ctx]} __{self.namespace}_global 0")
                self.commands.append(f"scoreboard players operation __intermediate_{self.intermediate[ctx]} __{self.namespace}_global -= __intermediate_{self.intermediate[ctx.getChild(1)]} __{self.namespace}_global")

        elif ctx.getChildCount() == 1:
            self.result[ctx] = self.result[ctx.getChild(0)]
            self.commands.append(f"scoreboard players set __intermediate_{self.intermediate[ctx]} __{self.namespace}_global {self.result[ctx]}")

    def exitDataStmt(self, ctx: MCCDPParser.DataStmtContext):
        super().exitDataStmt(ctx)

    def exitScoreStmt(self, ctx: MCCDPParser.ScoreStmtContext):
        namespaced_id = ctx.namespacedId()
        namespace = namespaced_id


    def exitStart_(self, ctx: MCCDPParser.Start_Context):
        for i in range(0, ctx.getChildCount(), 2):
            print(self.result[ctx.getChild(i)])
        print("-----------")
        for k, v in self.intermediate.items():
            print(k.getText(), v)
        print("-----------")
        for c in self.commands:
            print(c)
