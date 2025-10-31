import json
import os
from collections import defaultdict
from typing import Any

from antlr4 import ParserRuleContext

from built_in_functions import BUILT_IN_FUNCTIONS
from gen.MCCDPParser import MCCDPParser
from gen.MCCDPListener import MCCDPListener
from bidict import bidict

from mcc_types import *
from command_gen import *

import re

from settings import OUTPUT_PATH


class ListenerInterp(MCCDPListener):
    def __init__(self, mode: str = 'file'):
        self.mode = mode
        self.result: dict[ParserRuleContext, Any] = {}
        self.affiliations = set()
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
        key = str(Function.from_whole_path(self.namespace, self.scope))
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
            elif function.name == "at":
                return ExecuteAtModifier(args["selector"])
            else:
                raise NotImplementedError(f"Unsupported built-in function {function.name}")
        else:
            if not args:
                self.add_command(FunctionCommandGenerator(function))
        return None

    def enter_scope(self, name=None):
        if name is None:
            number = self.scope_counters[tuple(self.scope)]
            self.scope_counters[tuple(self.scope)] += 1
            self.scope.append(str(number))
        else:
            number = self.scope_counters[tuple(self.scope + [name])]
            self.scope_counters[tuple(self.scope + [name])] += 1
            self.scope += [name, str(number)]

    def leave_scope(self):
        last = self.scope.pop()
        if last.isdigit() and len(self.scope) > 0:
            if not self.scope[-1].isdigit():
                if self.scope[-1] in ["if", "for", "while", "withf"]:
                    self.scope.pop()

    def get_lval(self, namespaced_id: NamespacedID, current_scope: list[str]):
        current_scope = current_scope.copy()
        if namespaced_id.id in BUILT_IN_FUNCTIONS:
            return BUILT_IN_FUNCTIONS[namespaced_id.id]
        while True:
            definition_key = (*current_scope, str(namespaced_id))
            if definition_key in self.definitions:
                return self.definitions[definition_key]
            if len(current_scope) == 0:
                break
            else:
                current_scope.pop()
        raise ValueError(f"Undefined variable {namespaced_id.id}")

    def enterEveryRule(self, ctx):
        # return
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
        self.result[ctx] = self.get_lval(self.analyse_namespaced_id(ctx.namespacedId()), current_scope=self.scope)

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

    def mark_affiliated(self, ctx: MCCDPParser.BlockStmtContext):
        self.affiliations.add(ctx)

    def enterFunctionStatement(self, ctx: MCCDPParser.FunctionStatementContext):
        name_ctx: MCCDPParser.NamespacedIdContext = ctx.namespacedId()
        name = self.analyse_namespaced_id(name_ctx)
        decorator_ctx: MCCDPParser.DecoratorContext = ctx.decorator()
        if decorator_ctx is not None:
            function_tag = self.analyse_namespaced_id(decorator_ctx.namespacedIdSingleColon())
            self.function_tags[str(function_tag)].append(Function(name.namespace, name.id, [], self.scope))
        self.scope_ready = name.id
        self.definitions[(*self.scope, str(name))] = Function(name.namespace, name.id, [], self.scope)

    def enterBlock(self, ctx: MCCDPParser.BlockContext):
        if self.scope_ready is not None:
            if isinstance(ctx.parentCtx, MCCDPParser.FunctionStatementContext):
                self.scope += [self.scope_ready]
            else:
                self.enter_scope(self.scope_ready)
            self.scope_ready = None
        elif ctx not in self.affiliations:
            self.enter_scope()

    def exitBlock(self, ctx: MCCDPParser.BlockContext):
        self.result[ctx] = Function(self.namespace, self.scope[-1], [], self.scope[:-1])
        if ctx not in self.affiliations:
            self.leave_scope()

    def exitBlockStmt(self, ctx: MCCDPParser.BlockStmtContext):
        self.result[ctx] = self.result[ctx.block()]

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
        executor = None
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

            self.result[ctx] = self.call_function(to_call, final_args)

    def exitSelector(self, ctx: MCCDPParser.SelectorContext):
        variant = ctx.getChild(0).getText()[1:]
        args_ctx: MCCDPParser.ArgListContext = ctx.argList()
        args: list[SelectorArgument] = []
        if args_ctx is not None:
            for i, arg_ctx in enumerate(args_ctx.children):
                if arg_ctx.ID() is not None:
                    args.append(SelectorArgument(arg_ctx.ID().getText(), self.result[arg_ctx.expr()]))
                else:
                    args.append(SelectorArgument(i, self.result[arg_ctx.expr()]))
        self.result[ctx] = Selector(variant, args)

    def exitSelectorExpr(self, ctx: MCCDPParser.SelectorExprContext):
        self.result[ctx] = self.result[ctx.selector()]

    def exitCompareExpr(self, ctx: MCCDPParser.CompareExprContext):
        expr1_ctx: MCCDPParser.ExprContext = ctx.expr(0)
        expr2_ctx: MCCDPParser.ExprContext = ctx.expr(1)
        op = ctx.getChild(1).getText()
        result1 = self.result[expr1_ctx]
        result2 = self.result[expr2_ctx]
        if isinstance(result1, Scoreboard) and isinstance(result2, Scoreboard):
            self.result[ctx] = ScoreCompare(result1, result2, op)
        elif isinstance(result1, IntConstant) and isinstance(result2, IntConstant):
            if op == "==":
                self.result[ctx] = BooleanConstant(result1.value == result2.value)
            elif op == "!=":
                self.result[ctx] = BooleanConstant(result1.value != result2.value)
            elif op == ">":
                self.result[ctx] = BooleanConstant(result1.value > result2.value)
            elif op == ">=":
                self.result[ctx] = BooleanConstant(result1.value >= result2.value)
            elif op == "<":
                self.result[ctx] = BooleanConstant(result1.value < result2.value)
            elif op == "<=":
                self.result[ctx] = BooleanConstant(result1.value <= result2.value)
        elif isinstance(result1, Scoreboard) and isinstance(result2, IntConstant):
            if op == "==":
                self.result[ctx] = ScoreMatch(result1, Range(result2.value, result2.value))
            elif op == "!=":
                self.result[ctx] = NotLogic(ScoreMatch(result1, Range(result2.value, result2.value)))
            elif op == ">":
                self.result[ctx] = ScoreMatch(result1, Range(result2.value + 1, None))
            elif op == ">=":
                self.result[ctx] = ScoreMatch(result1, Range(result2.value, None))
            elif op == "<":
                self.result[ctx] = ScoreMatch(result1, Range(None, result2.value - 1))
            elif op == "<=":
                self.result[ctx] = ScoreMatch(result1, Range(None, result2.value))
        elif isinstance(result1, Scoreboard) and isinstance(result2, Range):
            if op == "==":
                self.result[ctx] = ScoreMatch(result1, result2)
            elif op == "!=":
                self.result[ctx] = NotLogic(ScoreMatch(result1, result2))
            elif op == ">":
                self.result[ctx] = ScoreMatch(result1, Range(result2.end + 1, None))
            elif op == ">=":
                self.result[ctx] = ScoreMatch(result1, Range(result2.start, None))
            elif op == "<":
                self.result[ctx] = ScoreMatch(result1, Range(None, result2.start - 1))
            elif op == "<=":
                self.result[ctx] = ScoreMatch(result1, Range(None, result2.end))
        else:
            raise NotImplementedError(f"Comparison values between {type(result1)} and {type(result2)} are not supported")  # TODO

    def enterIfStmt(self, ctx: MCCDPParser.IfStmtContext):
        if isinstance(ctx.statement(0), MCCDPParser.BlockStmtContext):
            self.scope_ready = "if"
        else:
            self.enter_scope("if")

    def exitIfStmt(self, ctx: MCCDPParser.IfStmtContext):
        condition_ctx: MCCDPParser.ExprContext = ctx.expr()
        condition = self.result[condition_ctx]
        statement_ctx: MCCDPParser.StatementContext = ctx.statement(0)
        if not isinstance(statement_ctx, MCCDPParser.BlockStmtContext):
            scope = self.scope.copy()
            self.leave_scope()
            key = str(Function.from_whole_path(self.namespace, scope))
            if len(self.commands[key]) == 0:
                del self.commands[key]
                return
            elif len(self.commands[key]) == 1:
                command = self.commands[key][0]
                del self.commands[key]
            else:
                function = Function.from_whole_path(self.namespace, scope, [])
                command = FunctionCommandGenerator(function)
        else:
            statement = self.result[statement_ctx]
            function = statement
            command = FunctionCommandGenerator(function)
        if isinstance(condition, ScoreCompare):
            self.add_command(ExecuteRunCommandGenerator([ExecuteIfScoreCompareCommandGenerator(condition.score1, condition.score2, condition.operation)], command))
        elif isinstance(condition, BooleanConstant):
            if condition.value:
                self.add_command(command)
        elif isinstance(condition, ScoreMatch):
            self.add_command(ExecuteRunCommandGenerator([ExecuteIfScoreMatchCommandGenerator(condition.score, condition.range)], command))
        else:
            raise NotImplementedError(f"Condition of type {type(condition)} is not supported")

    def exitPostIncDecExpr(self, ctx: MCCDPParser.PostIncDecExprContext):
        expr_ctx: MCCDPParser.LvalContext = ctx.expr()
        lval = self.result[expr_ctx]
        if isinstance(lval, Scoreboard):
            intermediate_scoreboard = self.intermediate_scoreboard(self.create_intermediate(), lval.scale)
            self.op_scoreboard(intermediate_scoreboard, lval, "=")
            self.result[ctx] = intermediate_scoreboard
            if ctx.getChild(1).getText() == "++":
                self.add_scoreboard(lval, 1)
            elif ctx.getChild(1).getText() == "--":
                self.remove_scoreboard(lval, 1)

    def exitPreIncDecExpr(self, ctx: MCCDPParser.PreIncDecExprContext):
        expr_ctx: MCCDPParser.LvalContext = ctx.expr()
        lval = self.result[expr_ctx]
        if isinstance(lval, Scoreboard):
            if ctx.getChild(0).getText() == "++":
                self.add_scoreboard(lval, 1)
            elif ctx.getChild(0).getText() == "--":
                self.remove_scoreboard(lval, 1)
            self.result[ctx] = lval

    def exitAssignExpr(self, ctx: MCCDPParser.AssignExprContext):
        lval_ctx: MCCDPParser.LvalContext = ctx.expr(0)
        lval = self.result[lval_ctx]
        expr_ctx: MCCDPParser.ExprContext = ctx.expr(1)
        expr = self.result[expr_ctx]
        if isinstance(lval, Scoreboard):
            if isinstance(expr, IntConstant):
                self.set_scoreboard(lval, expr.value)
            elif isinstance(expr, Scoreboard):
                self.op_scoreboard(lval, expr, "=")
            else:
                raise NotImplementedError(f"Assigning {type(expr)} to scoreboard is not supported.")

    def exitMemberExpr(self, ctx: MCCDPParser.MemberExprContext):
        pass

    def enterWithStmt(self, ctx: MCCDPParser.WithStmtContext):
        statement_ctx: MCCDPParser.StatementContext = ctx.statement()
        if isinstance(statement_ctx, MCCDPParser.BlockStmtContext):
            self.mark_affiliated(statement_ctx.block())
        self.enter_scope("with")

    def exitWithStmt(self, ctx: MCCDPParser.WithStmtContext):
        function = Function.from_whole_path(self.namespace, self.scope, [])
        self.leave_scope()
        commands = self.commands[str(function)]
        if len(commands) == 0:
            del self.commands[str(function)]
            return
        elif len(commands) == 1:
            command = commands[0]
            del self.commands[str(function)]
        else:
            command = FunctionCommandGenerator(function)
        expr_ctx = ctx.expr()
        expr = self.result[expr_ctx]
        if isinstance(expr, Selector):
            self.add_command(ExecuteRunCommandGenerator([ExecuteAsCommandGenerator(expr)], command))
        elif isinstance(expr, ExecuteAtModifier):
            self.add_command(ExecuteRunCommandGenerator([ExecuteAtCommandGenerator(expr.selector)], command))

    def exitStart_(self, ctx: MCCDPParser.Start_Context):
        # 后处理
        entrance_function = Function(self.namespace, ENTRANCE_FUNCTION, [], [])
        self.function_tags["minecraft:load"].insert(0, entrance_function)
        self.commands[str(entrance_function)].insert(0, ScoreboardObjectivesAddCommandGenerator(self.namespace, "__global", "dummy", f'"{self.namespace} globals"'))

        # 输出结果
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
            tag_namespace, tag_name = k.split(":", 1)
            tag_path = OUTPUT_PATH + f"data/{tag_namespace}/tags/function/"
            print(f"{k}")
            os.makedirs(tag_path, exist_ok=True)
            data = {"values": []}
            for function in v:
                list_item_str = str(function)
                print(f"- {list_item_str}")
                data["values"].append(list_item_str)
            with open(f"{tag_path}{tag_name}.json", "w") as f:
                json.dump(data, f, indent=4)
            print()
        print()
        print("[COMMANDS]")
        for k, v in self.commands.items():
            namespace, path_str = k.split(":", 1)
            path = f"{OUTPUT_PATH}data/{namespace}/function/" + "".join(i + "/" for i in path_str.split("/")[:-1])
            name = path_str.split("/")[-1] + ".mcfunction"
            os.makedirs(path, exist_ok=True)
            with open(path + name, "w") as f:
                print(k)
                print("-----------")
                for i in v:
                    f.write(str(i) + "\n")
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
