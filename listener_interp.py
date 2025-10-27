from collections import defaultdict

from gen.MCCDPParser import MCCDPParser
from gen.MCCDPListener import MCCDPListener
from bidict import bidict

from mcc_types import *
from command_gen import *

import re


class ListenerInterp(MCCDPListener):
    def __init__(self):
        self.result = {}
        self.intermediate = {}
        self.commands = defaultdict(list)
        self.current_id = 0
        self.internal_identifiers = bidict()
        self.var_types = {}
        self.namespace = "mydp"
        self.scope = []

    def create_intermediate(self):
        intermediate = self.current_id
        self.current_id += 1
        return Intermediate(intermediate)

    def add_command(self, command):
        if len(self.scope) == 0:
            key = ".init"
        elif len(self.scope) == 1:
            key = self.scope[0]
        else:
            key = ".internal/" + ".".join(self.scope)
        self.commands[key].append(command)
        print(f"{key}: {command}")

    def set_scoreboard(self, scoreboard: Scoreboard, value: int):
        self.add_command(ScoreboardPlayersSetCommandGenerator(scoreboard, value))

    def set_data(self, data: DataPath, value):
        pass

    def global_scoreboard(self, scope, name):
        return Scoreboard(self.namespace, "__global", scope, name)

    def intermediate_scoreboard(self, intermediate: Intermediate):
        return self.global_scoreboard(["__intermediate"], intermediate.id)

    def op_scoreboard(self, scoreboard1: Scoreboard, scoreboard2: Scoreboard, op):
        self.add_command(f"scoreboard players operation {scoreboard1} {op} {scoreboard2}")

    def enterEveryRule(self, ctx):
        if isinstance(ctx, MCCDPParser.StatementContext):
            self.add_command("# " + re.sub(r"\s+", " ", ctx.getText()))

    def exitInt(self, ctx: MCCDPParser.IntContext):
        if ctx.INT_DEC() is not None:
            value = int(ctx.INT_DEC().getText())
        elif ctx.INT_HEX() is not None:
            value = int(ctx.INT_HEX().getText(), 16)
        else:
            value = 0
        if ctx.INT_TYPE() is not None:
            int_type = ctx.INT_TYPE().getText()
        else:
            int_type = ""
        self.result[ctx] = IntConstant(value, int_type)

    def exitLiteral(self, ctx: MCCDPParser.LiteralContext):
        self.result[ctx] = self.result[ctx.getChild(0)]

    def exitAtom(self, ctx: MCCDPParser.AtomContext):
        if ctx.literal() is not None:
            self.result[ctx] = self.result[ctx.literal()]

    def exitDataStmt(self, ctx: MCCDPParser.DataStmtContext):
        super().exitDataStmt(ctx)

    def exitAtomExpr(self, ctx: MCCDPParser.AtomExprContext):
        self.result[ctx] = self.result[ctx.atom()]

    def exitAdditiveExpr(self, ctx: MCCDPParser.AdditiveExprContext):
        expr1_ctx: MCCDPParser.ExprContext = ctx.expr(0)
        expr2_ctx: MCCDPParser.ExprContext = ctx.expr(1)
        op = ctx.getChild(1).getText()
        result1 = self.result[expr1_ctx]
        result2 = self.result[expr2_ctx]
        if isinstance(result1, IntConstant) and isinstance(result2, IntConstant):
            if op == "+":
                self.result[ctx] = IntConstant(result1.value + result2.value)
            elif op == "-":
                self.result[ctx] = IntConstant(result1.value - result2.value)
            else:
                raise ValueError(f"Unknown operator {op}")

    def exitScoreStmt(self, ctx: MCCDPParser.ScoreStmtContext):
        scaling_factor_ctx: MCCDPParser.ScalingFactorContext | None = ctx.scalingFactor()
        if scaling_factor_ctx is not None:
            scaling_factor = float(scaling_factor_ctx.REAL().getText())
        else:
            scaling_factor = 1.0
        namespaced_id_ctx: MCCDPParser.NamespacedIdContext = ctx.namespacedId()
        namespace, id1 = self.analyse_namespaced_id(namespaced_id_ctx)
        expr_ctx: MCCDPParser.ExprContext = ctx.expr()
        if expr_ctx is not None:
            expr_result = self.result[expr_ctx]
        else:
            expr_result = None
        print(scaling_factor, namespace, id1, expr_result)
        if isinstance(expr_result, IntConstant):
            self.set_scoreboard(self.global_scoreboard(self.scope, id1), int(expr_result.value * scaling_factor))
        print('-----------')

    def analyse_namespaced_id(self, ctx: MCCDPParser.NamespacedIdContext):
        if ctx.getChildCount() == 1:
            return self.namespace, ctx.getText()
        else:
            return ctx.getChild(0).getText(), ctx.getChild(2).getText()

    def exitStart_(self, ctx: MCCDPParser.Start_Context):
        for k, v in self.commands.items():
            print(k)
            print("-----------")
            for i in v:
                print(i)
            print()
        # for i in range(0, ctx.getChildCount(), 2):
        #     print(self.result[ctx.getChild(i)])
        # print("-----------")
        # for k, v in self.intermediate.items():
        #     print(k.getText(), v)
        # print("-----------")
        # for c in self.commands:
        #     print(c)
