from typing import Any

from mcc_types import *

BUILT_IN_FUNCTIONS = {
    "say": BuiltInFunction("say", [FunctionArgument("message", Any)])
}