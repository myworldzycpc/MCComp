from mcc_types import Scoreboard


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
    def __init__(self, subcommand: str, scoreboard: Scoreboard):
        super().__init__()
        self.subcommand = subcommand
        self.scoreboard = scoreboard

    def get_params(self) -> list[str]:
        return super().get_params() + ["players", self.subcommand, self.scoreboard.final_name(), self.scoreboard.final_objective()]

class ScoreboardPlayersSetCommandGenerator(ScoreboardPlayersCommandGenerator):
    def __init__(self, scoreboard: Scoreboard, value: int):
        super().__init__("set", scoreboard)
        self.value = value

    def get_params(self) -> list[str]:
        return super().get_params() + [str(self.value)]