from abc import ABC, abstractmethod
from typing import Any

from settings import INTERNAL_PATH, ENTRANCE_FUNCTION


class VariableType(ABC):
    pass


class Intermediate:
    def __init__(self, id1):
        self.id = id1

    def __str__(self):
        return str(self.id)


class Field:
    def __init__(self, immutable):
        self.immutable = immutable


class Scoreboard(Field, VariableType):
    def __init__(self, namespace, objective, scope, name, scale: int | float = 1.0, immutable=False):
        super().__init__(immutable)
        self.namespace = namespace
        self.objective = objective
        self.scope = scope
        self.name = name
        self.scale = scale

    def final_objective(self):
        return f"{self.namespace}.{self.objective}"

    def final_name(self):
        return f"{"".join(i + "." for i in self.scope)}{self.name}"

    def __str__(self):
        return self.final_name() + " " + self.final_objective()

    def __repr__(self):
        return f"Scoreboard(namespace='{self.namespace}', objective='{self.objective}', scope={self.scope}, name='{self.name}', scale={self.scale})"


class DataPath(Field, VariableType):
    def __init__(self, immutable=False):
        super().__init__(immutable)


class StorageDataPath(DataPath):
    def __init__(self, namespace, id1, scope, name, immutable=False):
        super().__init__(immutable)
        self.namespace = namespace
        self.id = id1
        self.scope = scope
        self.name = name

    def final_name(self):
        return f"{self.namespace}:{self.id}"

    def final_path(self):
        return f"\"{"".join(i + "." for i in self.scope)}{self.name}\""

    def __str__(self):
        return f"{self.final_name()} {self.final_path()}"


class Constant:
    def __init__(self, value):
        self.value = value

    def parsed_value(self):
        return str(self.value)


class IntConstant(Constant):
    def __init__(self, value: int, int_type: str = ""):
        super().__init__(value)
        self.type = int_type.lower() or "i"
        if self.type not in ["b", "s", "i", "l", "f", "d"]:
            raise ValueError(f"Invalid type {self.type} for IntConstant")

    def __str__(self):
        return f"{self.value}{self.type if self.type != 'i' else ''}"

    def parsed_value(self):
        return str(self.value)


class FloatConstant(Constant):
    def __init__(self, value: float, float_type: str = ""):
        super().__init__(value)
        self.type = float_type.lower() or "d"
        if self.type not in ["f", "d"]:
            raise ValueError(f"Invalid type {self.type} for FloatConstant")

    def __str__(self):
        return f"{self.value}{self.type if self.type != 'd' else ''}"

    def parsed_value(self):
        return str(self.value)


class BooleanConstant(IntConstant):
    def __init__(self, value: bool):
        super().__init__(1 if value else 0, "b")

    def bool_value(self):
        return self.value != 0

    def __str__(self):
        return f"{'true' if self.value else 'false'}"


class StringConstant(Constant):
    def __init__(self, value: str):
        super().__init__(value)

    def __str__(self):
        return f"\"{self.value}\""

    def parsed_value(self):
        return self.value


class Range:
    def __init__(self, start: int | float | None = None, end: int | float | None = None):
        if start is not None and end is not None and start > end:
            raise ValueError("Start value cannot be greater than end value")
        self.start = start
        self.end = end

    def __str__(self):
        return f"{self.start or ''}..{self.end or ''}"


class NBTTag:
    def __init__(self):
        pass


class NBTInt:
    def __init__(self, value: IntConstant):
        super().__init__()
        self.value = value

    def __str__(self):
        return f"{self.value}"


class NamespacedID:
    def __init__(self, namespace, id1):
        self.namespace = namespace
        self.id = id1

    def __str__(self):
        return f"{self.namespace}:{self.id}"


class Function:
    def __init__(self, namespace, name, params: list["FunctionArgument"], scope=None, executor: "Selector" = None):
        if scope is None:
            scope = []
        self.namespace = namespace
        self.name = name
        self.scope = scope
        self.params = params
        self.executor = executor

    @classmethod
    def from_whole_path(cls, namespace, whole_path: list[str], params: list["FunctionArgument"] = None, executor: "Selector" = None):
        if params is None:
            params = []
        if len(whole_path) == 0:
            return Function(namespace, ENTRANCE_FUNCTION, params, [])
        elif len(whole_path) == 1:
            return Function(namespace, whole_path[0], params, [])
        else:
            return Function(namespace, whole_path[-1], params, whole_path[:-1])

    def __repr__(self):
        return f"Function(namespace='{self.namespace}', name='{self.name}', args={self.params}, scope={self.scope})"

    def __str__(self):
        if not self.scope:
            return f"{self.namespace}:{self.name}"
        else:
            return f"{self.namespace}:{INTERNAL_PATH}{'.'.join(self.scope + [self.name])}"


class BuiltInFunction(Function):
    def __init__(self, name, params: list["FunctionArgument"]):
        super().__init__("__builtin", name, params)

    def __repr__(self):
        return f"BuiltInFunction(name='{self.name}', args={self.params})"


class FunctionArgument:
    def __init__(self, name, type, default=None):
        self.name = name
        self.type = type
        self.default = default


class Selector:
    def __init__(self, variant, args: list["SelectorArgument"] = None):
        self.variant = variant
        if args is None:
            args = []
        self.args = args

    def __str__(self):
        return f"@{self.variant}{f"[{', '.join(str(arg) for arg in self.args)}]" if self.args else ''}"

    def __repr__(self):
        return f"Selector(variant='{self.variant}', args={self.args})"


class SelectorArgument:
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __str__(self):
        return f"{self.name}={self.value}"

    def __repr__(self):
        return f"SelectorArgument(name='{self.name}', value='{self.value}')"


class Command:
    def __init__(self, args: list[Any]):
        self.args = args

    def __str__(self):
        return " ".join(str(arg) for arg in self.args)

    def __repr__(self):
        return f"Command(args={self.args})"


class ConcreteOperation(ABC):
    def __init__(self, executor: "Selector" = None):
        self.executor = executor

    @abstractmethod
    def to_commands(self) -> list[Command]: ...


class AbstractionOperation(ABC):
    pass


class RelationalOperation(AbstractionOperation, ABC):
    pass


class ScoreCompare(RelationalOperation):
    def __init__(self, score1: Scoreboard, score2: Scoreboard, operation: str):
        self.score1 = score1
        self.score2 = score2
        self.operation = operation


class ScoreMatch(RelationalOperation):
    def __init__(self, score: Scoreboard, range1: Range):
        self.score = score
        self.range = range1


class Wrapper:
    def __int__(self, wrapped_obj):
        self.wrapped_obj = wrapped_obj

    def get(self):
        return self.wrapped_obj


class NotLogic(Wrapper):
    def __init__(self, operation):
        super().__init__(operation)


class ExecutorModifier(ABC):
    pass


class ExecuteAsModifier(ExecutorModifier):
    def __init__(self, selector: Selector):
        self.selector = selector

class ExecuteAtModifier(ExecutorModifier):
    def __init__(self, selector: Selector):
        self.selector = selector

class ExecutorModifiers:
    def __init__(self, executor_modifiers: list[ExecutorModifier]):
        self.executor_modifiers = executor_modifiers
