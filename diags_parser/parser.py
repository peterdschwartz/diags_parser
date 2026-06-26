import sys
from logging import Logger
from typing import Callable, List, Optional

import diags_parser.lexer as lexer
from diags_parser.diag_ast import (
    ArrayExpression,
    BoundsExpression,
    DerivativeExpression,
    Expression,
    ExpressionStatement,
    FloatLiteral,
    FuncExpression,
    GenericOperatorExpression,
    Identifier,
    InfixExpression,
    IntegerLiteral,
    LogicalLiteral,
    PrefixExpression,
    Program,
    Statement,
    StringLiteral,
    SumExpression,
    TendencyExpression,
    WhereExpression,
)
from diags_parser.logging_configs import get_logger
from diags_parser.my_types import LineTuple, LogicalLineIterator, Precedence
from diags_parser.tokens import Token, TokenTypes
from diags_parser.tracing import Trace

precedences = {
    TokenTypes.ASSIGN: Precedence.EQUALS,
    TokenTypes.PTR: Precedence.EQUALS,
    TokenTypes.PLUS: Precedence.SUM,
    TokenTypes.MINUS: Precedence.SUM,
    TokenTypes.SLASH: Precedence.PRODUCT,
    TokenTypes.ASTERISK: Precedence.PRODUCT,
    TokenTypes.LPAREN: Precedence.CALL,
    TokenTypes.COLON: Precedence.BOUNDS,
    TokenTypes.PERCENT: Precedence.BOUNDS,
    TokenTypes.EXP: Precedence.PRODUCT,
    TokenTypes.EQUIV: Precedence.EQUALS,
    TokenTypes.NOT_EQUIV: Precedence.EQUALS,
    TokenTypes.GT: Precedence.LESSGREATER,
    TokenTypes.GTEQ: Precedence.LESSGREATER,
    TokenTypes.LT: Precedence.LESSGREATER,
    TokenTypes.LTEQ: Precedence.LESSGREATER,
    TokenTypes.AND: Precedence.EQUALS,
    TokenTypes.OR: Precedence.EQUALS,
    TokenTypes.CONCAT: Precedence.PRODUCT,
    TokenTypes.BANG: Precedence.PREFIX,
    TokenTypes.DOT: Precedence.SUM,
}

PrefixParseFn = Callable[[], Expression]
InfixParseFn = Callable[[Expression], Expression]

Tok = TokenTypes


class ParseError(Exception):
    pass


class Parser:
    def __init__(
        self,
        lex: Optional[lexer.Lexer] = None,
        logger: str = "Parser",
        lines: list[LineTuple] = None,
    ):
        if lex:
            self.lexer: lexer.Lexer = lex
        elif lines:
            line_it = LogicalLineIterator(lines=lines)
            self.lexer = lexer.Lexer(line_it)
        else:
            sys.exit("Error - Need either lexer or lines to create Parser")
        self.errors: list[str] = []
        self.cur_token: Token = Token(token=Tok.ILLEGAL, literal="")
        self.peek_token: Token = Token(token=Tok.ILLEGAL, literal="")
        self.prefix_parse_fns: dict[Tok, PrefixParseFn] = {}
        self.infix_parse_fns: dict[Tok, InfixParseFn] = {}
        self.logger: Logger = get_logger(logger)

        self.lineno: int = 0

        self.register_prefix_fns(Tok.IDENT, self.parse_identifier)
        self.register_prefix_fns(Tok.INT, self.parseIntegerLiteral)
        self.register_prefix_fns(Tok.FLOAT, self.parse_FloatLiteral)
        self.register_prefix_fns(Tok.STRING, self.parseStringLiteral)
        self.register_prefix_fns(Tok.LOGICAL, self.parseLogicalLiteral)
        self.register_prefix_fns(Tok.BANG, self.parse_prefix_expr)
        self.register_prefix_fns(Tok.MINUS, self.parse_prefix_expr)
        self.register_prefix_fns(Tok.PLUS, self.parse_prefix_expr)
        self.register_prefix_fns(Tok.LPAREN, self.parse_grouped_expr)
        self.register_prefix_fns(Tok.COLON, self.parse_prefix_bounds_expr)
        self.register_prefix_fns(Tok.ASTERISK, self.stdout_or_fmt)
        self.register_prefix_fns(Tok.ARRAY_LBRACKET, self.parse_array_init)

        # Infix Operators
        self.register_infix_fns(Tok.PLUS, self.parse_infix_expr)
        self.register_infix_fns(Tok.MINUS, self.parse_infix_expr)
        self.register_infix_fns(Tok.SLASH, self.parse_infix_expr)
        self.register_infix_fns(Tok.ASTERISK, self.parse_infix_expr)
        self.register_infix_fns(Tok.EXP, self.parse_infix_expr)
        self.register_infix_fns(Tok.ASSIGN, self.parse_infix_expr)
        self.register_infix_fns(Tok.PTR, self.parse_infix_expr)
        self.register_infix_fns(Tok.CONCAT, self.parse_infix_expr)
        self.register_infix_fns(Tok.LPAREN, self.parse_func_expr)
        self.register_infix_fns(Tok.COLON, self.parse_infix_bounds_expr)
        # Logical operators
        self.register_infix_fns(Tok.EQUIV, self.parse_infix_expr)
        self.register_infix_fns(Tok.GT, self.parse_infix_expr)
        self.register_infix_fns(Tok.LT, self.parse_infix_expr)
        self.register_infix_fns(Tok.GTEQ, self.parse_infix_expr)
        self.register_infix_fns(Tok.LTEQ, self.parse_infix_expr)
        self.register_infix_fns(Tok.NOT_EQUIV, self.parse_infix_expr)
        self.register_infix_fns(Tok.AND, self.parse_infix_expr)
        self.register_infix_fns(Tok.OR, self.parse_infix_expr)
        #
        self.register_infix_fns(Tok.DOT, self.parse_infix_expr)

        self.next_token()
        self.next_token()

    def reset_lexer(self, lex: lexer.Lexer):
        """
        Function to reuse parser with new input/lexer
        """
        self.lexer = lex
        self.next_token()
        self.next_token()

    def next_token(self):
        """
        function to advance tokens
        """
        self.cur_token = self.peek_token
        self.peek_token = self.lexer.next_token()
        self.lexer.token_pos += 1

        # self.logger.debug(f"{self.cur_token} -> {self.peek_token}")
        self.lineno = self.lexer.cur_ln
        return

    def is_first_token(self) -> bool:
        return self.lexer.token_pos == 1

    def register_prefix_fns(self, tok_type: Tok, fn: PrefixParseFn):
        self.prefix_parse_fns[tok_type] = fn

    def register_infix_fns(self, tok_type: Tok, fn: InfixParseFn):
        self.infix_parse_fns[tok_type] = fn

    @Trace.trace_decorator("parse_identifier")
    def parse_identifier(self) -> Expression:
        return Identifier(tok=self.cur_token, value=self.cur_token.literal)

    def parseIntegerLiteral(self) -> Expression:
        lit = self.cur_token.literal
        if "_" in lit:
            val, prec = lit.split("_")
            val = int(val)
        else:
            val = int(lit)
            prec = ""
        return IntegerLiteral(tok=self.cur_token, val=val, prec=prec)

    def parseStringLiteral(self) -> Expression:
        return StringLiteral(tok=self.cur_token, val=self.cur_token.literal)

    def parseLogicalLiteral(self) -> Expression:
        val_str = self.cur_token.literal
        if val_str == ".true.":
            val = True
        else:
            val = False
        return LogicalLiteral(tok=self.cur_token, val=val)

    def parse_FloatLiteral(self) -> Expression:
        lit = self.cur_token.literal
        precision = ""
        if "_" in lit:
            val_prec = lit.split("_")
            val = val_prec[0]
            prec = "_".join(val_prec[1:])
            precision = "_" + prec
        else:
            val = lit
        value = float(val.replace("d", "e"))
        num = FloatLiteral(tok=self.cur_token, val=value, prec=precision)
        return num

    def curTokenIs(self, etype: Tok):
        return self.cur_token.token == etype

    def peekTokenIs(self, etype: Tok):
        return self.peek_token.token == etype

    def expect_peek_and_advance(self, etype: Tok) -> bool:
        if self.peekTokenIs(etype):
            self.next_token()
            return True
        else:
            err = f"Expected: {etype}, Got: {self.peek_token} @{self.lineno} {self.lexer.input}"
            self.errors.append(err)
            self.logger.error(f"{err}")
            return False

    def peek_precedence(self) -> Precedence:
        try:
            prec = precedences[self.peek_token.token]
            return prec
        except KeyError:
            return Precedence.LOWEST

    def cur_precedence(self) -> Precedence:
        try:
            prec = precedences[self.cur_token.token]
            return prec
        except KeyError:
            return Precedence.LOWEST

    def parse_program(self) -> Program:
        program = Program()
        while self.cur_token.token != Tok.EOF:
            try:
                stmt = self.parse_statement()
                if stmt:
                    program.statements.append(stmt)
            except ParseError as e:
                self.logger.error(f"Error: {e}")
            self.next_token()
            if self.errors:
                self.error_exit()
        return program

    def error_exit(self):
        for err in self.errors:
            self.logger.error(f"{err}")
        sys.exit(1)

    def check_label(self) -> Optional[Token]:
        """
        If the current token is an identifier followed by a colon,
        treat it as a named block label.
        This function should only be called on the first Token of a Statement
        """
        label = None
        if self.cur_token.token == Tok.IDENT and self.peek_token.token == Tok.COLON:
            label = self.cur_token
            self.next_token()  # skip IDENT
            self.next_token()  # skip COLON
        return label

    def wrap_assert(self, cond, msg):
        assert cond, f"{msg}\n{self.lexer.line_iter.get_curr_line()}"

    def stdout_or_fmt(self) -> Expression:
        return IOExpression(self.cur_token)

    @Trace.trace_decorator("parse_statement")
    def parse_statement(self) -> Optional[Statement]:
        label = self.check_label()

        startln = self.lineno
        match self.cur_token.token:
            case Tok.NEWLINE:
                stmt = None
            case Tok.SEMICOLON:
                stmt = None
            case _:
                stmt = self.parse_expression_statement()
        if stmt:
            stmt.lineno = startln
        return stmt

    def parse_expression_statement(self) -> ExpressionStatement:
        stmt = ExpressionStatement(tok=self.cur_token)
        stmt.expression = self.parse_expression(Precedence.LOWEST)
        # self.next_token()
        return stmt

    @Trace.trace_decorator("parse_expression")
    def parse_expression(self, prec: Precedence) -> Expression:
        cur_type = self.cur_token.token
        prefix = self.prefix_parse_fns.get(cur_type, None)
        if not prefix:
            err = f"Unexpected Token {cur_type} at {self.lineno} {self.lexer.input}"
            self.logger.error(err)
            self.errors.append(err)
            sys.exit(1)
        left_expr: Expression = prefix()

        while (
            not self.peekTokenIs(Tok.NEWLINE)
            and prec.value < self.peek_precedence().value
        ):
            peek_type = self.peek_token.token
            if peek_type not in self.infix_parse_fns:
                print(f"{peek_type} not in infix_parse_fns!!")
                return left_expr
            infix = self.infix_parse_fns[peek_type]
            self.next_token()
            left_expr = infix(left_expr)
        return left_expr

    @Trace.trace_decorator("parse_grouped_expr")
    def parse_grouped_expr(self) -> Expression:
        """
        Parses grouped expression
        """
        self.next_token()

        expr = self.parse_expression(Precedence.LOWEST)
        if not self.expect_peek_and_advance(Tok.RPAREN):
            self.errors.append("Failed to Parse Grouped Expression" + str(expr))
        return expr

    @Trace.trace_decorator("parse_prefix_expr")
    def parse_prefix_expr(self) -> Expression:
        tok = self.cur_token
        op = tok.literal
        self.next_token()
        right_expr = self.parse_expression(Precedence.PREFIX)
        expr = PrefixExpression(tok=tok, op=op, right=right_expr)

        return expr

    @Trace.trace_decorator("parse_infix_expr")
    def parse_infix_expr(self, left: Expression) -> Expression:
        """
        (parse_infix_expr)
        """
        tok = self.cur_token
        op = self.cur_token.literal
        prec = self.cur_precedence()
        self.next_token()

        right_expr = self.parse_expression(prec)
        expression = InfixExpression(
            tok=tok,
            op=op,
            left=left,
            right=right_expr,
        )
        return expression

    @Trace.trace_decorator("parse_func_expr")
    def parse_func_expr(self, func: Expression) -> Expression:
        tok = self.cur_token
        args = self.parse_args()
        match func.token_literal().strip():
            case "where":
                self.wrap_assert(
                    cond=bool(len(args) == 1), msg="WhereExpression only takes one arg"
                )
                func_expr = WhereExpression(tok=tok, condition=args[0])
            case "sum":
                self.wrap_assert(
                    cond=bool(len(args) == 1 ),
                    msg=f"SumExpression only takes 1 args\n{[str(arg) for arg in args]}",
                )
                func_expr = SumExpression(tok=tok, arg=args[0])
            case "derivative":
                self.wrap_assert(
                    cond=bool(len(args) == 2),
                    msg="DerivativeExpression must have 2 args",
                )
                func_expr = DerivativeExpression(tok=tok, args=args)
            case "tend":
                self.wrap_assert(
                    cond=bool(len(args)==0),
                    msg="TendencyExpression doesn't take any arguments"
                )
                func_expr = TendencyExpression(tok=tok)
            case _:
                func_expr = FuncExpression(tok=tok, fn=func, args=args)

        return func_expr

    @Trace.trace_decorator("parse_args")
    def parse_args(self) -> list[Expression]:
        args: list[Expression] = []

        if self.peekTokenIs(Tok.RPAREN):
            self.next_token()
            return args
        self.next_token()
        args.append(self.parse_expression(Precedence.LOWEST))
        while self.peekTokenIs(Tok.COMMA):
            self.next_token()
            self.next_token()
            # Current token is now start of next arg
            args.append(self.parse_expression(Precedence.LOWEST))

        # Note expect peek advances tokens, to cur_token = RPAREN at return
        if not self.expect_peek_and_advance(Tok.RPAREN):
            raise ParseError("Couldn't Parse Arguments")
        return args

    @Trace.trace_decorator("parse_infix_bounds_expr")
    def parse_infix_bounds_expr(self, start: Expression) -> Expression:
        """
        Function to parse bounds.  curent token should be ":"
        """
        tok = self.cur_token
        start_ = start
        end_ = None
        if not self.peekTokenIs(Tok.RPAREN) and not self.peekTokenIs(Tok.COMMA):
            self.next_token()
            end_ = self.parse_expression(Precedence.LOWEST)
        return BoundsExpression(tok=tok, start=start_, end=end_)

    @Trace.trace_decorator("parse_prefix_bounds_expr")
    def parse_prefix_bounds_expr(self) -> Expression:
        """
        Function to parse bounds.  curent token should be ":"
        """
        tok = self.cur_token
        end_ = None
        if not self.peekTokenIs(Tok.RPAREN) and not self.peekTokenIs(Tok.COMMA):
            self.next_token()
            end_ = self.parse_expression(Precedence.LOWEST)
        return BoundsExpression(tok=tok, start=None, end=end_)

    @Trace.trace_decorator("parse_array_init")
    def parse_array_init(self) -> Expression:
        start_tok = self.cur_token
        end_tok = Tok.ARRAY_RBRACKET

        elements: list[Expression] = []
        implied_do = None
        while not self.curTokenIs(end_tok):
            self.next_token()
            item_expr = self.parse_expression(Precedence.LOWEST)
            elements.append(item_expr)
            self.next_token()

        return ArrayExpression(
            tok=start_tok,
            elements=elements,
        )
