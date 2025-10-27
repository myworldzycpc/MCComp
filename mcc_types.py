class Intermediate:
    def __init__(self, id1):
        self.id = id1

    def __str__(self):
        return str(self.id)


class Scoreboard:
    def __init__(self, namespace, objective, scope, name):
        self.namespace = namespace
        self.objective = objective
        self.scope = scope
        self.name = name

    def final_objective(self):
        return f"{self.namespace}.{self.objective}"

    def final_name(self):
        return f"{"".join(i + "." for i in self.scope)}{self.name}"

    def __str__(self):
        return self.final_name() + " " + self.final_objective()


class DataPath:
    def __init__(self, namespace, id1, scope, name):
        self.namespace = namespace
        self.id = id1
        self.scope = scope
        self.name = name

    def __str__(self):
        return f"{self.namespace}:{self.id} \"{"".join(i + "." for i in self.scope)}{self.name}\""


class Constant:
    def __init__(self):
        pass


class IntConstant(Constant):
    def __init__(self, value: int, int_type: str = ""):
        super().__init__()
        self.value = value
        self.type = int_type.lower() or "i"
        if self.type not in ["b", "s", "i", "l", "f", "d"]:
            raise ValueError(f"Invalid type {self.type} for IntConstant")

    def __str__(self):
        return f"{self.value}{self.type if self.type != 'i' else ''}"
