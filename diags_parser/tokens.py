from dataclasses import dataclass
from enum import Enum


class TokenTypes(Enum):
    IDENT = "IDENT"
    EOF = "EOF"
    INT = "INT"
    FLOAT = "FLOAT"
    STRING = "STRING"
    ILLEGAL = "ILLEGAL"
    # Operators
    ASSIGN = "="
    PLUS = "+"
    MINUS = "-"
    ASTERISK = "*"
    BANG = ".not."
    SLASH = "/"
    EXP = "**"
    EQUIV = "=="
    GT = ">"
    GTEQ = ">="
    LT = "<"
    LTEQ = "<="
    NOT_EQUIV = "ne"
    OR = "or"
    AND = "and"
    CONCAT = "//"
    PTR = "=>"
    DOT = "."
    # delimiters
    COMMA = ","
    LPAREN = "("
    RPAREN = ")"
    NEWLINE = "\n"
    COLON = ":"
    SEMICOLON = ';'
    PERCENT = "%"
    DOUBLE_COLON = "::"
    ARRAY_LBRACKET = "["
    ARRAY_RBRACKET = "]"

    # keywords
    LOGICAL = "LOGICAL"
    RETURN = "RETURN"
    WHERE = "where"
    DIVERGENCE = "divergence"
    DERIVATIVE = "derivative"
    INTEGRAL = "integral"
    SUM = "sum"
    TEND = "tendency"


keywords: dict[str, TokenTypes] = {
    ".true.": TokenTypes.LOGICAL,
    ".false.": TokenTypes.LOGICAL,
    "eq": TokenTypes.EQUIV,
    "gt": TokenTypes.GT,
    "lt": TokenTypes.LT,
    "not": TokenTypes.BANG,
    "ne": TokenTypes.NOT_EQUIV,
    "ge": TokenTypes.GTEQ,
    "le": TokenTypes.LTEQ,
    "and": TokenTypes.AND,
    "or": TokenTypes.OR,
    # "where" : TokenTypes.WHERE,
    # "div" : TokenTypes.DIVERGENCE,
    # "deriv": TokenTypes.DERIVATIVE,
    # "int" : TokenTypes.INTEGRAL,
    # "sum" : TokenTypes.SUM,
    # "tend" : TokenTypes.TEND,
}


@dataclass
class Token:
    token: TokenTypes
    literal: str

    def __str__(self):
        return f"{self.literal}[{self.token}]"


def lookup_identifer(ident: str) -> TokenTypes:
    if ident in keywords:
        return keywords[ident]
    return TokenTypes.IDENT


OPERATORS = {
    TokenTypes.ASSIGN,
    TokenTypes.PLUS,
    TokenTypes.MINUS,
    TokenTypes.ASTERISK,
    TokenTypes.BANG,
    TokenTypes.SLASH,
    TokenTypes.EXP,
    TokenTypes.EQUIV,
    TokenTypes.GT,
    TokenTypes.GTEQ,
    TokenTypes.LT,
    TokenTypes.LTEQ,
    TokenTypes.NOT_EQUIV,
    TokenTypes.OR,
    TokenTypes.AND,
    TokenTypes.CONCAT,
    TokenTypes.PTR,
}
