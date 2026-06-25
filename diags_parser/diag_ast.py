import json
from abc import ABC, abstractmethod
from copy import deepcopy
from typing import List, Optional, Tuple

from diags_parser.tokens import Token, TokenTypes


# helpers
def NOT(x):
    return PrefixExpression(tok=Token(TokenTypes.BANG, ".not."), op=".not.", right=x)


def AND(a, b):
    return InfixExpression(
        tok=Token(TokenTypes.AND, ".and."), left=a, op=".and.", right=b
    )


class SemanticError(Exception):
    pass


# Base interface: Node
class Node(ABC):
    @abstractmethod
    def token_literal(self) -> str:
        """Return the literal value of the token."""
        pass

    @abstractmethod
    def __str__(self) -> str:
        pass


# Derived interface: Statement
class Statement(Node):
    def __init__(self, lineno: int = -1):
        self.lineno: int = lineno

    @abstractmethod
    def statement_node(self) -> None:
        """Marker method for statement nodes."""
        pass

    def to_dict(self):
        return {"Node": self.__class__.__name__}


# Derived interface: Expression
class Expression(Node):
    @abstractmethod
    def expression_node(self) -> None:
        """Marker method for expression nodes."""
        pass

    def to_dict(self):
        return {"Node": self.__class__.__name__}


class Program(Statement):
    def __init__(self):
        self.statements: List[Statement] = []

    def token_literal(self) -> str:
        if len(self.statements) > 0:
            return self.statements[0].token_literal()
        else:
            return ""

    def statement_node(self) -> None:
        pass

    def __str__(self):
        return "\n".join(str(stmt) for stmt in self.statements)


class Identifier(Expression):
    def __init__(self, tok: Token, value: str):
        self.token = tok
        self.value: str = value

    def token_literal(self) -> str:
        return self.token.literal

    def __str__(self) -> str:
        return self.value

    def __repr__(self):
        return f"Ident({self.value})"

    def expression_node(self) -> None:
        pass

    def __eq__(self, other):
        return isinstance(other, Identifier) and self.value == other.value

    def get_name(self) -> str:
        return f"{self.value}"

    def to_dict(self):
        return {"Node": "Ident", "Val": str(self)}


# Statement Classes
class ExpressionStatement(Statement):
    def __init__(self, tok: Token):
        self.token = tok
        self.expression: Expression

    def statement_node(self):
        pass

    def token_literal(self) -> str:
        return self.token.literal

    def __str__(self):
        return str(self.expression)

    def __eq__(self, other):
        if not isinstance(other, ExpressionStatement):
            return False
        else:
            return self.token == other.token and self.expression == other.expression

    def to_dict(self):
        return {"Node": "ExpressionStatement", "Expr": self.expression.to_dict()}

    def copy(self):
        return deepcopy(self)


class SubCallStatement(Statement):
    def __init__(self, tok):
        self.token: Token = tok  # "CALL"
        self.function: FuncExpression  # FuncExpression

    def statement_node(self):
        pass

    def token_literal(self) -> str:
        return self.token.literal

    def __str__(self):
        return "CALL " + str(self.function)

    def __eq__(self, other):
        if not isinstance(other, SubCallStatement):
            return False
        else:
            return self.token == other.token and self.function == other.function

    def to_dict(self):
        return {"Node": "SubCallStatement", "Sub": self.function.to_dict()}

    def copy(self):
        return deepcopy(self)


class IntegerLiteral(Expression):
    def __init__(self, tok: Token, val: int, prec: str):
        self.token: Token = tok
        self.value: int = val
        self.precision: str = prec

    def token_literal(self) -> str:
        return str(self.value)

    def expression_node(self) -> None:
        pass

    def __str__(self):
        return self.token_literal()

    def __eq__(self, other):
        return isinstance(other, IntegerLiteral) and self.value == other.value

    def to_dict(self):
        return {"Node": "IntegerLiteral", "Val": self.value, "Prec": self.precision}


class StringLiteral(Expression):
    def __init__(self, tok: Token, val: str):
        self.token: Token = tok  # SQUOTE or DQUOTE
        self.value: str = val

    def token_literal(self) -> str:
        return str(self.value)

    def expression_node(self) -> None:
        pass

    def __str__(self):
        return f"'{self.value}'"

    def __eq__(self, other):
        return isinstance(other, StringLiteral) and self.value == other.value

    def to_dict(self):
        return {"Node": "StringLiteral", "Val": self.value}


class LogicalLiteral(Expression):
    def __init__(self, tok: Token, val: bool):
        self.token: Token = tok
        self.value: bool = val

    def token_literal(self) -> str:
        return str(self.value)

    def expression_node(self) -> None:
        pass

    def __str__(self):
        return self.token_literal()

    def __eq__(self, other):
        return isinstance(other, LogicalLiteral) and self.value == other.value

    def to_dict(self):
        return {"Node": "LogicalLiteral", "Val": self.value}


class FloatLiteral(Expression):
    def __init__(self, tok: Token, val: float, prec: str):
        self.token: Token = tok
        self.value: float = val
        self.precision: str = prec

    def token_literal(self) -> str:
        return self.token.literal

    def expression_node(self) -> None:
        pass

    def __str__(self):
        return str(self.value)

    def __eq__(self, other):
        return isinstance(other, FloatLiteral) and self.value == other.value

    def to_dict(self):
        return {"Node": "FloatLiteral", "Val": self.value}


class PrefixExpression(Expression):
    def __init__(self, tok: Token, op: str, right: Expression):
        self.token: Token = tok
        self.right_expr: Expression = right
        self.operator: str = op

    def token_literal(self) -> str:
        return self.token.literal

    def expression_node(self) -> None:
        pass

    def __str__(self):
        return f"{self.operator} ({str(self.right_expr)})"

    def __eq__(self, other):
        if not isinstance(other, PrefixExpression):
            return False
        else:
            return (
                self.token == other.token
                and self.right_expr == other.right_expr
                and self.operator == other.operator
            )

    def to_dict(self):
        return {
            "Node": "PrefixExpression",
            "Op": self.operator,
            "Right": self.right_expr.to_dict(),
        }

    def copy(self):
        return deepcopy(self)


class InfixExpression(Expression):
    def __init__(
        self,
        tok: Token,
        left: Expression,
        op: str,
        right: Expression,
    ):
        self.token: Token = tok
        self.left_expr: Expression = left
        self.operator: str = op
        self.right_expr: Expression = right

    def expression_node(self) -> None:
        pass

    def token_literal(self) -> str:
        return self.token.literal

    def decompose(self) -> Tuple[Expression, str, Expression]:
        return (self.left_expr, self.operator, self.right_expr)

    def __str__(self):
        return str(self.left_expr) + f" {self.operator} " + str(self.right_expr)

    def __eq__(self, other):
        if not isinstance(other, InfixExpression):
            return False
        else:
            return (
                self.token == other.token
                and self.right_expr == other.right_expr
                and self.operator == other.operator
                and self.left_expr == other.left_expr
            )

    def copy(self):
        return deepcopy(self)

    def to_dict(self):
        return {
            "Node": "InfixExpression",
            "Left": self.left_expr.to_dict(),
            "Op": self.operator,
            "Right": self.right_expr.to_dict(),
        }


class FuncExpression(Expression):
    """
    Expression for functions or arrays. Infix operator expression
    """

    def __init__(self, tok: Token, fn: Identifier, args: list[Expression]):
        self.token: Token = tok  # '('
        assert isinstance(fn, Identifier)
        self.function: Identifier = fn  # Identifier
        self.args: list[Expression] = args

    def expression_node(self) -> None:
        pass

    def token_literal(self) -> str:
        return self.token.literal

    def get_name(self) -> str:
        return self.function.value

    def __str__(self):
        args = ",".join(str(arg) for arg in self.args)
        return str(self.function) + "(" + args + ")"

    def __eq__(self, other):
        if not isinstance(other, FuncExpression):
            return False
        else:
            return (
                self.token == other.token
                and self.function == other.function
                and self.args == other.args
            )

    def to_dict(self):
        return {
            "Node": "FuncExpression",
            "Func": str(self.function),
            "Args": [arg.to_dict() for arg in self.args],
        }

    def copy(self):
        return deepcopy(self)


class BoundsExpression(Expression):
    def __init__(self, tok, start: Optional[Expression], end=Optional[Expression]):
        self.token: Token = tok  # Colon
        self.start = start
        self.end = end

    def expression_node(self) -> None:
        pass

    def token_literal(self) -> str:
        return super().token_literal()

    def __str__(self):
        s = "" if self.start is None else self.start
        e = "" if self.end is None else self.end
        return f"{s}:{e}"

    def __eq__(self, other):
        if not isinstance(other, BoundsExpression):
            return False
        else:
            return (
                self.token == other.token
                and self.start == other.start
                and self.end == other.end
            )

    def to_dict(self):
        return {
            "Node": "BoundsExpression",
            "Val": str(self),
            "Start": self.start.to_dict() if self.start else None,
            "End": self.end.to_dict() if self.end else None,
        }

    def copy(self):
        return deepcopy(self)


class GenericOperatorExpression(Expression):
    def __init__(self, tok: Token, spec: Identifier):
        assert tok.literal in {"operator", "assignment"}
        self.token: Token = tok
        self.interface: Identifier = spec

    def expression_node(self) -> None:
        pass

    def token_literal(self) -> str:
        return self.token.literal

    def __str__(self) -> str:
        return f"{self.token_literal()}({self.interface})"

    def to_dict(self):
        return {
            "Node": "GenericOperatorExpression",
            "Token": self.token_literal(),
            "Interface": self.interface.value,
        }


class ArrayExpression(Expression):
    def __init__(self, tok: Token, elements: list[Expression]):
        self.token = tok
        self.elements = elements.copy()

    def expression_node(self) -> None:
        pass

    def token_literal(self) -> str:
        return self.token.literal

    def __str__(self) -> str:
        els = [str(el) for el in self.elements]
        return f"[ {','.join(els)} ]"

    def to_dict(self) -> dict:
        return {"Node": "ArrayExpr", "Elements": [el.to_dict() for el in self.elements]}


class WhereExpression(Expression):
    def __init__(self, tok: Token, condition: Expression):
        self.token = tok
        self.condition = condition

    def expression_node(self) -> None:
        pass

    def token_literal(self) -> str:
        return self.token.literal

    def __str__(self) -> str:
        return f"WHERE({self.condition})"

    def to_dict(self) -> dict:
        return {
            "Node": "WhereExpr",
            "Condition": self.condition.to_dict(),
        }


class SumExpression(Expression):
    def __init__(self, tok: Token, arg: Expression):
        dims = self._init_args(arg)
        self.token = tok
        self.dims = dims

    def expression_node(self) -> None:
        pass

    def token_literal(self) -> str:
        return self.token.literal

    def __str__(self) -> str:
        return f"SUM(dims={self.dims})"

    def to_dict(self) -> dict:
        return {
            "Node": "SumExpr",
            "Dimensions": self.dims.to_dict(),
        }

    def _init_args(self, arg: Expression):
        if isinstance(arg, InfixExpression):
            assert arg.operator == "="
            dims = arg.right_expr
        else:
            dims = arg
        assert isinstance(dims, ArrayExpression)
        return dims


class TendencyExpression(Expression):
    def __init__(self, tok: Token):
        self.token = tok

    def expression_node(self) -> None:
        pass

    def token_literal(self) -> str:
        return self.token.literal

    def __str__(self) -> str:
        return f"TEND()"

    def to_dict(self) -> dict:
        return {"Node": "TendencyExpr"}


class DerivativeExpression(Expression):
    def __init__(self, tok: Token, args: list[Expression]):
        dx, dims = self._init_args(args)
        self.token = tok
        self.dx = dx
        self.dims: ArrayExpression = dims

    def expression_node(self) -> None:
        pass

    def token_literal(self) -> str:
        return self.token.literal

    def __str__(self) -> str:
        return f"{self.token_literal()}(dx={self.dx}, dims={self.dims})"

    def to_dict(self) -> dict:
        return {
            "Node": "DerivativeExpr",
            "dx": self.dx.to_dict(),
            "Dimensions": self.dims.to_dict(),
        }

    def _init_args(self, args: list[Expression]) -> tuple[Expression, ArrayExpression]:
        """
        from parsed arg string, resolve which is dx and dimension.
        so order does not matter for input.
        """
        dx = None
        dims = None
        for arg in args:
            assert isinstance(arg, InfixExpression) and arg.operator == "="
            if arg.left_expr.value == "dx":
                dx = arg.right_expr
            elif arg.left_expr.value == "dims":
                dims = arg.right_expr
        assert dx is not None, "couldn't determine dx for derivative"
        assert dims is not None and isinstance(
            dims, ArrayExpression
        ), "couldn't determine dimensions for derivative."
        return dx, dims


def expr_from_dict(d: dict | None) -> Optional[Expression]:
    if d is None:
        return None

    node = d.get("Node")
    match node:
        case "Ident":
            return Identifier(None, value=d["Val"])
        case "StringLiteral":
            return StringLiteral(tok=None, val=d["Val"])
        case "FloatLiteral":
            return FloatLiteral(tok=None, val=d["Val"], prec="")
        case "LogicalLiteral":
            return LogicalLiteral(None, val=d["Val"])
        case "IntegerLiteral":
            return IntegerLiteral(tok=None, val=d["Val"], prec=d["Prec"])
        case "PrefixExpression":
            return PrefixExpression(
                tok=None, op=d["Op"], right=expr_from_dict(d["Right"])
            )
        case "InfixExpression":
            return InfixExpression(
                tok=None,
                left=expr_from_dict(d["Left"]),  # <-- recursion
                op=d["Op"],
                right=expr_from_dict(d["Right"]),  # <-- recursion
            )
        case "FuncExpression":
            args = [expr_from_dict(arg) for arg in d["Args"]]
            return FuncExpression(tok=None, fn=d["Func"], args=args)
        case "FieldAccessExpression":
            return FieldAccessExpression(
                left=expr_from_dict(d["Left"]),
                field=expr_from_dict(d["Field"]),
                tok=None,
            )
        case "BoundsExpression":
            return BoundsExpression(
                tok=None,
                start=expr_from_dict(d["Start"]),
                end=expr_from_dict(d["End"]),
            )

    raise ValueError(f"Unknown node type: {node}")


def expr_to_json(expr) -> str:
    """Serialize an Expression to a canonical JSON string."""
    if expr is None:
        return "null"
    return json.dumps(expr.to_dict(), separators=(",", ":"), sort_keys=True)


def expr_from_json(s: str) -> Optional[Expression]:
    """Deserialize a JSON string into an Expression (or None)."""
    d = json.loads(s)
    return expr_from_dict(d)  # your function
