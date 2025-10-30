from collections import defaultdict
from typing import Any

from built_in_functions import BUILT_IN_FUNCTIONS
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
        self.definitions = {}
        self.current_id = 0
        self.internal_identifiers = bidict()
        self.var_types = {}
        self.namespace = "mydp"
        self.scope = []
        self.scope_ready = None
        self.scope_counters = defaultdict(int)
        self.function_tags = defaultdict(list)
        self.amend = False

    def create_intermediate(self):
        intermediate = self.current_id
        self.current_id += 1
        return Intermediate(intermediate)

    def add_command(self, command, mode=None):
        if len(self.scope) == 0:
            key = ".init"
        elif len(self.scope) == 1:
            key = self.scope[0]
        else:
            key = ".internal/" + ".".join(self.scope)
        if mode == "prepend":
            self.commands[key].insert(0, command)
        else:
            if self.amend:
                self.commands[key][-1] += command
            else:
                self.commands[key].append(command)
            self.amend = mode == "amend"
        print(f"{key}: {command}{f' ({mode})' if mode else ''}")

    def set_scoreboard(self, scoreboard: Scoreboard, value: float):
        self.add_command(ScoreboardPlayersSetCommandGenerator(scoreboard, int(value * scoreboard.scale)))

    def add_scoreboard(self, scoreboard: Scoreboard, value: float):
        self.add_command(ScoreboardPlayersAddCommandGenerator(scoreboard, int(value * scoreboard.scale)))

    def remove_scoreboard(self, scoreboard: Scoreboard, value: float):
        self.add_command(ScoreboardPlayersRemoveCommandGenerator(scoreboard, int(value * scoreboard.scale)))

    def set_data(self, data: StorageDataPath, value):
        self.add_command(DataModifyStorageSetValueCommandGenerator(data, value))

    def global_scoreboard(self, scope, name, scaling_factor: int | float = 1, namespace=None):
        return Scoreboard(namespace or self.namespace, "__global", scope, name, scaling_factor)

    def intermediate_scoreboard(self, intermediate: Intermediate, scale=1):
        return self.global_scoreboard(["__intermediate"], intermediate.id, scale)

    def op_scoreboard(self, scoreboard1: Scoreboard, scoreboard2: Scoreboard, op):
        if scoreboard1.scale == scoreboard2.scale:
            self.add_command(ScoreboardPlayersOperationCommandGenerator(scoreboard1, scoreboard2, op))
        else:
            if op == "=":
                self.add_command(ScoreboardPlayersOperationCommandGenerator(scoreboard1, scoreboard2, op))
                intermediate = self.create_intermediate()
                intermediate_scoreboard = self.intermediate_scoreboard(intermediate)
                if scoreboard1.scale < scoreboard2.scale:
                    self.set_scoreboard(intermediate_scoreboard, scoreboard2.scale / scoreboard1.scale)
                    self.op_scoreboard(scoreboard1, intermediate_scoreboard, "/=")
                else:
                    self.set_scoreboard(intermediate_scoreboard, scoreboard1.scale / scoreboard2.scale)
                    self.op_scoreboard(scoreboard1, intermediate_scoreboard, "*=")
            elif op == "*=" or op == "/=":
                if scoreboard2.scale == 1:
                    self.add_command(ScoreboardPlayersOperationCommandGenerator(scoreboard1, scoreboard2, op))

    def call_function(self, function: Function, args: dict[str, Any] = None):
        if isinstance(function, BuiltInFunction):
            if function.name == "say":
                message = args["message"]
                if isinstance(message, Constant):
                    message_str = message.parsed_value()
                    self.add_command(SayCommandGenerator(message_str))
        else:
            if not args:
                self.add_command(FunctionCommandGenerator(function))

    def enter_scope(self, name=None):
        if name is None:
            number = self.scope_counters[tuple(self.scope)] + 1
            self.scope_counters[tuple(self.scope)] += 1
            self.scope.append(str(number))
        else:
            number = self.scope_counters[tuple(self.scope + [name])] + 1
            self.scope_counters[tuple(self.scope + [name])] += 1
            self.scope += [name, str(number)]

    def leave_scope(self):
        # todo: 最后一位是数字，则检查前一位，如果是某些值则接着跳出
        last = self.scope.pop()
        if last.isdigit() and len(self.scope) > 0:
            if not self.scope[-1].isdigit():
                if self.scope[-1] in ["if", "for", "while"]:
                    self.scope.pop()

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
        if ctx.typeProfix() is not None:
            int_type = ctx.typeProfix().getText()
        else:
            int_type = ""
        self.result[ctx] = IntConstant(value, int_type)

    def exitLiteral(self, ctx: MCCDPParser.LiteralContext):
        if ctx.getChild(0) in self.result:
            self.result[ctx] = self.result[ctx.getChild(0)]
            return
        else:
            if ctx.STRING() is not None:
                value = ctx.STRING().getText()[1:-1]
                self.result[ctx] = StringConstant(value)
                return
        raise NotImplementedError("Unsupported literal")

    def exitAtom(self, ctx: MCCDPParser.AtomContext):
        if ctx.literal() is not None:
            self.result[ctx] = self.result[ctx.literal()]

    def exitDataStmt(self, ctx: MCCDPParser.DataStmtContext):
        super().exitDataStmt(ctx)

    def exitAtomExpr(self, ctx: MCCDPParser.AtomExprContext):
        self.result[ctx] = self.result[ctx.atom()]

    def exitLval(self, ctx: MCCDPParser.LvalContext):
        if ctx.getChildCount() > 1:
            raise NotImplementedError("Complex lvals not supported")  # TODO
        else:
            namespaced_id = self.analyse_namespaced_id(ctx.namespacedId())
            definition_key = (*self.scope, str(namespaced_id))
            if definition_key in self.definitions:
                self.result[ctx] = self.definitions[definition_key]
            elif namespaced_id.id in BUILT_IN_FUNCTIONS:
                self.result[ctx] = BUILT_IN_FUNCTIONS[namespaced_id.id]
            else:
                raise ValueError(f"Undefined variable {namespaced_id.id}")

    def exitLvalExpr(self, ctx: MCCDPParser.LvalExprContext):
        self.result[ctx] = self.result[ctx.lval()]

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
        if isinstance(result1, Scoreboard) and isinstance(result2, IntConstant):
            if op == "+":
                intermediate = self.create_intermediate()
                intermediate_scoreboard = self.intermediate_scoreboard(intermediate, result1.scale)
                self.op_scoreboard(intermediate_scoreboard, result1, "=")
                self.add_scoreboard(intermediate_scoreboard, result2.value)
                self.result[ctx] = intermediate_scoreboard
            elif op == "-":
                intermediate = self.create_intermediate()
                intermediate_scoreboard = self.intermediate_scoreboard(intermediate, result1.scale)
                self.op_scoreboard(intermediate_scoreboard, result1, "=")
                self.remove_scoreboard(intermediate_scoreboard, result2.value)
                self.result[ctx] = intermediate_scoreboard
            else:
                raise ValueError(f"Unknown operator {op}")

    def exitScoreStmt(self, ctx: MCCDPParser.ScoreStmtContext):
        scaling_factor_ctx: MCCDPParser.ScalingFactorContext | None = ctx.scalingFactor()
        if scaling_factor_ctx is not None:
            if scaling_factor_ctx.expr() is not None:
                scaling_factor_expr_ctx = self.result[scaling_factor_ctx.expr()]
                if isinstance(scaling_factor_expr_ctx, IntConstant):
                    scaling_factor = scaling_factor_expr_ctx.value
                elif isinstance(scaling_factor_expr_ctx, FloatConstant):
                    scaling_factor = scaling_factor_expr_ctx.value
                else:
                    raise ValueError("Scaling factor should be a constant")
            else:
                scaling_factor = 1
        else:
            scaling_factor = 1
        namespaced_id_ctx: MCCDPParser.NamespacedIdContext = ctx.namespacedId()
        namespaced_id = self.analyse_namespaced_id(namespaced_id_ctx)
        namespace = namespaced_id.namespace
        id1 = namespaced_id.id
        expr_ctx: MCCDPParser.ExprContext = ctx.expr()
        if expr_ctx is not None:
            expr_result = self.result[expr_ctx]
        else:
            expr_result = None
        scoreboard = self.global_scoreboard(self.scope, id1, scaling_factor, namespace)
        self.definitions[(*self.scope, str(namespaced_id))] = scoreboard
        if isinstance(expr_result, IntConstant):
            self.set_scoreboard(scoreboard, expr_result.value)
        elif isinstance(expr_result, Scoreboard):
            self.op_scoreboard(scoreboard, expr_result, "=")

    def analyse_namespaced_id(self, ctx: MCCDPParser.NamespacedIdContext | MCCDPParser.NamespacedIdSingleColonContext):
        if ctx.getChildCount() == 1:
            return NamespacedID(self.namespace, ctx.getText())
        else:
            return NamespacedID(ctx.getChild(0).getText(), ctx.getChild(2).getText())

    def enterFunctionStatement(self, ctx: MCCDPParser.FunctionStatementContext):
        name_ctx: MCCDPParser.NamespacedIdContext = ctx.namespacedId()
        name = self.analyse_namespaced_id(name_ctx)
        decorator_ctx: MCCDPParser.DecoratorContext = ctx.decorator()
        if decorator_ctx is not None:
            function_tag = self.analyse_namespaced_id(decorator_ctx.namespacedIdSingleColon())
            self.function_tags[str(function_tag)].append((self.scope, name))
        self.scope_ready = name.id
        self.definitions[(*self.scope, str(name))] = Function(name.namespace, name.id, [], self.scope)

    def enterBlock(self, ctx: MCCDPParser.BlockContext):
        if self.scope_ready is not None:
            if isinstance(ctx.parentCtx, MCCDPParser.FunctionStatementContext):
                self.scope += [self.scope_ready]
            else:
                self.enter_scope(self.scope_ready)
            self.scope_ready = None
        else:
            self.enter_scope()

    def exitBlock(self, ctx: MCCDPParser.BlockContext):
        self.result[ctx] = Function(self.namespace, self.scope[-1], [], self.scope[:-1])
        self.leave_scope()

    def exitCallExpr(self, ctx: MCCDPParser.CallExprContext):
        to_call_ctx: MCCDPParser.ExprContext = ctx.expr()
        to_call = self.result[to_call_ctx]
        args_ctx: MCCDPParser.ArgListContext = ctx.argList()
        args = {}
        final_args = {}
        arg_ctx: MCCDPParser.ArgContext
        if args_ctx is not None:
            for i, arg_ctx in enumerate(args_ctx.children):
                if arg_ctx.ID() is not None:
                    args[arg_ctx.ID().getText()] = self.result[arg_ctx.expr()]
                else:
                    args[i] = self.result[arg_ctx.expr()]

        if isinstance(to_call, Function):
            for i, param in enumerate(to_call.params):
                if args.get(param.name) is not None:
                    if param.type is not Any and not isinstance(args[param.name], param.type):
                        raise TypeError(f"Argument {param.name} should be of type {param.type}, not {type(args[param.name])}")
                    else:
                        final_args[param.name] = args[param.name]
                elif args.get(i) is not None:
                    if param.type is not Any and not isinstance(args[i], param.type):
                        raise TypeError(f"Argument {param.name} should be of type {param.type}, not {type(args[i])}")
                    else:
                        final_args[param.name] = args[i]
                else:
                    final_args[param.name] = None

            self.call_function(to_call, final_args)

    def exitSelector(self, ctx: MCCDPParser.SelectorContext):
        variant = ctx.getChild(0).getText()[1:]
        args_ctx: MCCDPParser.ArgListContext = ctx.argList()
        args = {}
        # todo

    def exitCompareExpr(self, ctx: MCCDPParser.CompareExprContext):
        expr1_ctx: MCCDPParser.ExprContext = ctx.expr(0)
        expr2_ctx: MCCDPParser.ExprContext = ctx.expr(1)
        op = ctx.getChild(1).getText()
        result1 = self.result[expr1_ctx]
        result2 = self.result[expr2_ctx]
        if isinstance(result1, Scoreboard) and isinstance(result2, Scoreboard):
            self.result[ctx] = ScoreCompare(result1, result2, op)
        else:
            raise NotImplementedError("Comparison between non-scoreboard values not supported")  # TODO

    def enterIfStmt(self, ctx: MCCDPParser.IfStmtContext):
        if isinstance(ctx.statement(), MCCDPParser.BlockStmtContext):
            self.scope_ready = "if"
        else:
            self.enter_scope("if")

    def exitIfStmt(self, ctx: MCCDPParser.IfStmtContext):
        condition_ctx: MCCDPParser.ExprContext = ctx.expr()
        condition = self.result[condition_ctx]
        statement_ctx: MCCDPParser.StatementContext = ctx.statement()
        statement = self.result[statement_ctx]
        scope = self.scope.copy()
        if not isinstance(statement_ctx, MCCDPParser.BlockStmtContext):
            self.leave_scope()
        if len(self.commands.get(tuple(scope))) == 0:
            del self.commands[tuple(scope)]
        elif len(self.commands.get(tuple(scope))) == 1:
            command = self.commands[tuple(scope)][0]
        else:
            function = Function.from_whole_path()  # todo
        if isinstance(condition, ScoreCompare):
            self.add_command(ExecuteRunCommandGenerator([ExecuteIfScoreCompareCommandGenerator(condition.score1, condition.score2, condition.operation)], ))

    def exitStart_(self, ctx: MCCDPParser.Start_Context):
        print()
        print("-----------")
        print("[DEFINITIONS]")
        for k, v in self.definitions.items():
            print(f"{'.'.join(k):<20} {repr(v)} ({v})")
        print()
        print(f"[INTERMEDIATE] ({self.current_id})")
        for k, v in self.intermediate.items():
            print(f"{k}: {v}")
        print()
        print("[FUNCTION TAGS]")
        for k, v in self.function_tags.items():
            print(f"{k}")
            for scope, name in v:
                print(f"- {'.'.join(i.id for i in scope + [name])}")
            print()
        print()
        print("[COMMANDS]")
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
