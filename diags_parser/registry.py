from dataclasses import dataclass, field


@dataclass
class SupportedFunction:
    name: str
    desc: str
    args: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        arg_str = ",".join(self.args)
        return f"{self.name}({arg_str}) --- {self.desc}"


SUPPORTED = [
    SupportedFunction(
        name="where",
        desc="applies conditon to operand",
        args=["<boolean expression>"],
    ),
    SupportedFunction(
        name="sum",
        desc="sums operand over designated indices (int or name)",
        args=["dims=[..]"],
    ),
    SupportedFunction(
        name="derivative",
        desc="takes derivative w.r.t. `dx` over designated dimension",
        args=["dx", "dims=[..]"],
    ),
    SupportedFunction(
        name="tend",
        desc="calculates the tendency of a variable over time",
        args=[],
    ),
]
