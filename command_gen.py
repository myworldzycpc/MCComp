from mcc_types import *


class CommandGenerator:
    def __init__(self):
        pass

    def get_params(self) -> list[str]:
        return []

    def __str__(self):
        return " ".join(self.get_params())


class ScoreboardCommandGenerator(CommandGenerator):
    def __init__(self):
        super().__init__()

    def get_params(self) -> list[str]:
        return super().get_params() + ["scoreboard"]


class ScoreboardObjectivesCommandGenerator(ScoreboardCommandGenerator):
    def __init__(self):
        super().__init__()

    def get_params(self) -> list[str]:
        return super().get_params() + ["objectives"]


class ScoreboardPlayersCommandGenerator(ScoreboardCommandGenerator):
    def __init__(self):
        super().__init__()

    def get_params(self) -> list[str]:
        return super().get_params() + ["players"]


class ScoreboardPlayersSetCommandGenerator(ScoreboardPlayersCommandGenerator):
    def __init__(self, scoreboard: Scoreboard, value: int):
        super().__init__()
        self.scoreboard = scoreboard
        self.value = value

    def get_params(self) -> list[str]:
        return super().get_params() + ["set", self.scoreboard.final_name(), self.scoreboard.final_objective(), str(self.value)]


class ScoreboardPlayersAddCommandGenerator(ScoreboardPlayersCommandGenerator):
    def __init__(self, scoreboard: Scoreboard, value: int):
        super().__init__()
        self.scoreboard = scoreboard
        self.value = value

    def get_params(self) -> list[str]:
        return super().get_params() + ["add", self.scoreboard.final_name(), self.scoreboard.final_objective(), str(self.value)]


class ScoreboardPlayersRemoveCommandGenerator(ScoreboardPlayersCommandGenerator):
    def __init__(self, scoreboard: Scoreboard, value: int):
        super().__init__()
        self.scoreboard = scoreboard
        self.value = value

    def get_params(self) -> list[str]:
        return super().get_params() + ["remove", self.scoreboard.final_name(), self.scoreboard.final_objective(), str(self.value)]


class ScoreboardPlayersOperationCommandGenerator(ScoreboardPlayersCommandGenerator):
    def __init__(self, scoreboard: Scoreboard, scoreboard2: Scoreboard, operation: str):
        super().__init__()
        self.scoreboard = scoreboard
        self.scoreboard2 = scoreboard2
        self.operation = operation

    def get_params(self) -> list[str]:
        return super().get_params() + ["operation", self.scoreboard.final_name(), self.scoreboard.final_objective(), self.operation, self.scoreboard2.final_name(), self.scoreboard2.final_objective()]


class DataCommandGenerator(CommandGenerator):
    def __init__(self):
        super().__init__()

    def get_params(self):
        return super().get_params() + ["data"]


class DataModifyCommandGenerator(DataCommandGenerator):
    def __init__(self):
        super().__init__()

    def get_params(self):
        return super().get_params() + ["modify"]


class DataModifyStorageCommandGenerator(DataModifyCommandGenerator):
    def __init__(self, storage: StorageDataPath):
        super().__init__()
        self.storage = storage

    def get_params(self):
        return super().get_params() + ["storage", self.storage.final_name(), self.storage.final_path()]


class DataModifyStorageSetCommandGenerator(DataModifyStorageCommandGenerator):
    def __init__(self, storage: StorageDataPath):
        super().__init__(storage)

    def get_params(self):
        return super().get_params() + ["set"]


class DataModifyStorageSetValueCommandGenerator(DataModifyStorageSetCommandGenerator):
    def __init__(self, storage: StorageDataPath, value: NBTTag):
        super().__init__(storage)
        self.value = value

    def get_params(self) -> list[str]:
        return super().get_params() + [str(self.value)]


class FunctionCommandGenerator(CommandGenerator):
    def __init__(self, function: Function):
        super().__init__()
        self.function = function

    def get_params(self) -> list[str]:
        return super().get_params() + ["function", str(self.function)]


class SayCommandGenerator(CommandGenerator):
    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def get_params(self) -> list[str]:
        return super().get_params() + ["say", self.message]


class ExecuteCommandGenerator(CommandGenerator):
    def __init__(self, sub_commands: list["ExecuteSubCommandGenerator"]):
        super().__init__()
        self.sub_commands = sub_commands

    def get_params(self) -> list[str]:
        return super().get_params() + ["execute"] + [param for sub_command in self.sub_commands for param in sub_command.get_params()]


class ExecuteSubCommandGenerator(CommandGenerator):
    def __init__(self):
        super().__init__()


class ExecuteAsCommandGenerator(ExecuteSubCommandGenerator):
    def __init__(self, target: Selector):
        super().__init__()
        self.target = target

    def get_params(self) -> list[str]:
        return super().get_params() + ["as", str(self.target)]


class ExecuteAtCommandGenerator(ExecuteSubCommandGenerator):
    def __init__(self, target: Selector):
        super().__init__()
        self.target = target

    def get_params(self) -> list[str]:
        return super().get_params() + ["at", str(self.target)]

class ExecuteIfCommandGenerator(ExecuteSubCommandGenerator):
    def __init__(self):
        super().__init__()

    def get_params(self) -> list[str]:
        return super().get_params() + ["if"]

class ExecuteIfScoreCommandGenerator(ExecuteIfCommandGenerator):
    def __init__(self, scoreboard: Scoreboard):
        super().__init__()
        self.scoreboard = scoreboard

    def get_params(self) -> list[str]:
        return super().get_params() + ["score", self.scoreboard.final_name(), self.scoreboard.final_objective()]

class ExecuteIfScoreCompareCommandGenerator(ExecuteIfScoreCommandGenerator):
    def __init__(self, scoreboard1: Scoreboard, scoreboard2: Scoreboard, operation: str):
        super().__init__(scoreboard1)
        self.scoreboard2 = scoreboard2
        self.operation = operation

    def get_params(self) -> list[str]:
        return super().get_params() + [self.operation, self.scoreboard2.final_name(), self.scoreboard2.final_objective()]



class ExecuteRunCommandGenerator(ExecuteCommandGenerator):
    def __init__(self, sub_commands: list["ExecuteSubCommandGenerator"], command: CommandGenerator):
        super().__init__(sub_commands)
        self.command = command

    def get_params(self) -> list[str]:
        return super().get_params() + ["run", *self.command.get_params()]
