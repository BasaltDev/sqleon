# Copyright (C) 2026 BasaltDev
# SPDX-License-Identifier: GPL-3.0-only

# type: ignore
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum, auto
from typing import Any

from .lexer import Lexer, Token, TokenType, TokenTypeGroups, error


class Node:
    class LiteralType(Enum):
        Int = auto()
        Float = auto()
        String = auto()
        Boolean = auto()
        Null = auto()
        Identifier = auto()

    class Type:
        @dataclass
        class Int:
            def sqleon_format(self) -> str:
                return "INT"

            def matches_type(self, other: "Node.Type") -> bool:
                return isinstance(other, Node.Type.Int)

        @dataclass
        class Boolean:
            def sqleon_format(self) -> str:
                return "BOOLEAN"

            def matches_type(self, other: "Node.Type"):
                return isinstance(other, Node.Type.Boolean)

        @dataclass
        class Decimal:
            precision: int
            scale: int

            def sqleon_format(self) -> str:
                return f"DECIMAL({self.precision}, {self.scale})"

            def matches_type(self, other: "Node.Type") -> bool:
                return isinstance(other, Node.Type.Decimal) and (
                    other.scale,
                    other.precision,
                ) == (self.scale, self.precision)

        @dataclass
        class VarChar:
            length: int = 99999999

            def sqleon_format(self) -> str:
                return f"VARCHAR({self.length})"

            def matches_type(self, other: "Node.Type") -> bool:
                return (
                    isinstance(other, Node.Type.VarChar) and self.length <= other.length
                )

        @classmethod
        def resolve_name(self, name: str) -> "Node.Type":
            if name.startswith("VARCHAR"):
                return Node.Type.VarChar(int(name[8:-1]))
            elif name == "BOOLEAN":
                return Node.Type.Boolean()
            elif name == "INT":
                return Node.Type.Int()
            elif name == "DECIMAL":
                return Node.Type.Decimal(*list(map(int, name[8:-1].split(", "))))

        @classmethod
        def turn_value_into_type(self, value: Any) -> "Node.Type":
            if isinstance(value, str):
                return self.VarChar(len(value))
            elif isinstance(value, bool):
                return self.Boolean()
            elif isinstance(value, int):
                return self.Int()
            elif isinstance(value, Decimal):
                return self.Decimal(
                    len(value.as_tuple().digits), -value.as_tuple().exponent
                )

    @dataclass
    class Literal:
        type: "Node.LiteralType"
        value: Any
        line: tuple[int, int] = (-1, -1)
        column: tuple[int, int] = (-1, -1)

    class Expr: ...

    @dataclass
    class UnExpr(Expr):
        rhs: "Node.Expr"
        op: str
        line: tuple[int, int] = (-1, -1)
        column: tuple[int, int] = (-1, -1)

    @dataclass
    class BinExpr(Expr):
        lhs: "Node.Expr"
        rhs: "Node.Expr"
        op: str
        line: tuple[int, int] = (-1, -1)
        column: tuple[int, int] = (-1, -1)

    @dataclass
    class TrinExpr(Expr):
        lhs: "Node.Expr"
        mhs: "Node.Expr"
        rhs: "Node.Expr"
        op: str
        line: tuple[int, int] = (-1, -1)
        column: tuple[int, int] = (-1, -1)

    @dataclass
    class CreateTable:
        name: str
        columns: dict[str, dict[str, Any]]
        line: tuple[int, int] = (-1, -1)
        column: tuple[int, int] = (-1, -1)

    @dataclass
    class Select:
        to_select: "Node.Expr"
        line: tuple[int, int] = (-1, -1)
        column: tuple[int, int] = (-1, -1)

    @dataclass
    class Insert:
        table_name: str
        to_insert: "Node.Expr" | tuple["Node.Expr", ...]
        line: tuple[int, int] = (-1, -1)
        column: tuple[int, int] = (-1, -1)

    @dataclass
    class DropTable:
        to_drop: str
        line: tuple[int, int] = (-1, -1)
        column: tuple[int, int] = (-1, -1)


class Parser:
    def __init__(self, lexer: Lexer):
        self.operator_type_map = {
            "PLUS": "+",
            "MINUS": "-",
            "STAR": "*",
            "SLASH": "/",
            "EQUAL": "=",
            "NOTEQUAL": "!=",
            "LESSTHAN": "<",
            "GREATERTHAN": ">",
            "LESSTHANEQUAL": "<=",
            "GREATERTHANEQUAL": ">=",
        }
        self.tokens = lexer.lex()
        self.pos = -1
        self.ct: Token | None = None
        self.ast: list[Node] = []
        self.adv()
        self.keyword_handlers: dict[str, Callable[..., Any]] = {
            "CREATE": self.parse_create,
            "SELECT": self.parse_select,
            "INSERT": self.parse_insert,
            "DROP": self.parse_drop
        }

    def adv(self, amt: int = 1):
        self.pos += amt
        self.ct = None if self.pos >= len(self.tokens) else self.tokens[self.pos]

    def expect_token_type(self, token_type: TokenType, *other_types: list[TokenType]):
        if not self.ct or self.ct.type not in (token_type, *other_types):
            if self.ct:
                typename = f"`{self.ct.type.name.lower()}`"
            else:
                typename = "nothing"
                self.adv(-1)
            ttypes = [token_type, *other_types]
            ttypes = list(map(lambda x: x.name.lower(), ttypes))
            error.error(
                f"expected {' or '.join(ttypes)}, got {typename}",
                (self.ct.line, self.ct.column),
            )

    def expect_token_value_type(self, value_type: type):
        if not self.ct or not isinstance(self.ct.value, value_type):
            if self.ct:
                typename = f"`{type(self.ct.value).__name__.lower()}`"
            else:
                typename = "nothing"
                self.adv(-1)
            error.error(
                f"expected {value_type.__name__}, got {typename}",
                (self.ct.line, self.ct.column),
            )

    def expect_token_type_and_value_type(self, token_type: TokenType, value_type: type):
        self.expect_token_type(token_type)
        self.expect_token_value_type(value_type)

    def expect_token(self, token_type: TokenType, value: Any):
        if not self.ct or self.ct.type != token_type or self.ct.value != value:
            if self.ct:
                token_value = f"{self.ct.type.name.lower()} of value `{self.ct.value}`"
            else:
                token_value = "nothing"
                self.adv(-1)
            error.error(
                f"expected {token_type.name} of value `{value}`, got {token_value}",
                (self.ct.line, self.ct.column),
            )

    def parse_shebang(self, token: Token):
        value: str = token.value
        if value.startswith("db="):
            value = value.replace("db=", "")[1:-1]
        return value

    def make_token_literal(self, token: Token):
        if isinstance(token, (Node.Literal, Node.BinExpr, Node.UnExpr)):
            return token
        node_type: Node.LiteralType = Node.LiteralType.Null
        if token.type == TokenType.Number:
            node_type = (
                Node.LiteralType.Int
                if isinstance(token.value, int)
                else Node.LiteralType.Float
            )
        elif token.type == TokenType.String:
            node_type = Node.LiteralType.String
        elif token.type == TokenType.Boolean:
            node_type = Node.LiteralType.Boolean
        elif token.type == TokenType.Identifier:
            node_type = Node.LiteralType.Identifier
        return Node.Literal(
            node_type,
            token.value,
            (token.line, token.line),
            (token.column, token.column),
        )

    def parse_expression(
        self,
        ending: TokenType = TokenType.Semicolon,
        altEndings: tuple[TokenType | None] = (TokenType.EOF,),
    ) -> Node.Expr | Node.Literal:
        operands: list[Token | Node] = []
        operators: list[Token] = []
        last_item: Token | TokenType | None = None
        while self.ct and self.ct.type not in (ending, *altEndings):
            if self.ct.type in TokenTypeGroups.UnaryOperators and last_item in (
                *TokenTypeGroups.Operators,
                None,
            ):
                operators.append(
                    Token(
                        TokenTypeGroups.UnaryOperators[self.ct.type],
                        None,
                        self.ct.line,
                        self.ct.column,
                    )
                )
            elif self.ct.type == TokenType.LeftParen:
                self.adv()
                operands.append(self.parse_expression(ending=TokenType.RightParen))
            elif self.ct.type in TokenTypeGroups.Operators:
                operators.append(self.ct)
                last_item = self.ct.type
            elif self.ct.type == TokenType.Keyword:
                if self.ct.value == "BETWEEN":
                    operators.append(self.ct.type)
                    operands.append(self.parse_expression(ending=TokenType.And))
                    operands.append(self.parse_expression(ending, altEndings))
                    last_item = self.ct.type
            else:
                operands.append(self.make_token_literal(self.ct))
                last_item = operands[-1]
            self.adv()
        for i, op in list(
            filter(
                lambda op: op[1].type in TokenTypeGroups.UnaryOperators.values(),
                enumerate(operators),
            )
        ):
            value = operands[i]
            operands[i] = Node.UnExpr(
                value,
                self.operator_type_map.get(a := op.type.upper()) or a,
                (op.line, value.line[1]),
                (op.column, value.column[1]),
            )
            del operators[i]
        while any(
            betweens := list(
                filter(
                    lambda op: op[1].type == TokenType.Between,
                    enumerate(operators),
                )
            )
        ):
            for i, op in betweens:
                value1 = operands[i]
                value2 = operands[i + 1]
                value3 = operands[i + 2]
                operands[i] = Node.TrinExpr(
                    value1,
                    value2,
                    value3,
                    self.operator_type_map.get(a := op.type.name.upper()) or a,
                    (value1.line[1], value3.line[1]),
                    (value1.column[1], value3.column[1]),
                )
                del operators[i + 1]
                del operators[i]
                del operands[i + 2]
                del operands[i + 1]
                break

        while any(
            higher_arithmetics := list(
                filter(
                    lambda op: op[1].type in TokenTypeGroups.HigherArithmeticOperators,
                    enumerate(operators),
                )
            )
        ):
            for i, op in higher_arithmetics:
                value1 = operands[i]
                value2 = operands[i + 1]
                operands[i] = Node.BinExpr(
                    value1,
                    value2,
                    self.operator_type_map.get(a := op.type.name.upper()) or a,
                    (value1.line[1], value2.line[1]),
                    (value1.column[1], value2.column[1]),
                )
                del operators[i]
                del operands[i + 1]
                break

        while any(
            lower_arithmetics := list(
                filter(
                    lambda op: op[1].type in TokenTypeGroups.LowerArithmeticOperators,
                    enumerate(operators),
                )
            )
        ):
            for i, op in lower_arithmetics:
                value1 = operands[i]
                value2 = operands[i + 1]
                operands[i] = Node.BinExpr(
                    value1,
                    value2,
                    self.operator_type_map.get(a := op.type.name.upper()) or a,
                    (value1.line[1], value2.line[1]),
                    (value1.column[1], value2.column[1]),
                )
                del operators[i]
                del operands[i + 1]
                break

        while any(
            equalities := list(
                filter(
                    lambda op: op[1].type in TokenTypeGroups.EqualityOperators,
                    enumerate(operators),
                )
            )
        ):
            for i, op in equalities:
                value1 = operands[i]
                value2 = operands[i + 1]
                operands[i] = Node.BinExpr(
                    value1,
                    value2,
                    self.operator_type_map.get(a := op.type.name.upper()) or a,
                    (value1.line[1], value2.line[1]),
                    (value1.column[1], value2.column[1]),
                )
                del operators[i]
                del operands[i + 1]
                break

        while any(
            comparisons := list(
                filter(
                    lambda op: op[1].type in TokenTypeGroups.ComparisonOperators,
                    enumerate(operators),
                )
            )
        ):
            for i, op in comparisons:
                value1 = operands[i]
                value2 = operands[i + 1]
                operands[i] = Node.BinExpr(
                    value1,
                    value2,
                    self.operator_type_map.get(a := op.type.name.upper()) or a,
                    (value1.line[1], value2.line[1]),
                    (value1.column[1], value2.column[1]),
                )
                del operators[i]
                del operands[i + 1]
                break
        while any(
            ands := list(
                filter(
                    lambda op: op[1].type == TokenType.And,
                    enumerate(operators),
                )
            )
        ):
            for i, op in ands:
                value1 = operands[i]
                value2 = operands[i + 1]
                operands[i] = Node.BinExpr(
                    value1,
                    value2,
                    self.operator_type_map.get(a := op.type.name.upper()) or a,
                    (value1.line[1], value2.line[1]),
                    (value1.column[1], value2.column[1]),
                )
                del operators[i]
                del operands[i + 1]
                break
        while any(
            ors := list(
                filter(
                    lambda op: op[1].type == TokenType.Or,
                    enumerate(operators),
                )
            )
        ):
            for i, op in ors:
                value1 = operands[i]
                value2 = operands[i + 1]
                operands[i] = Node.BinExpr(
                    value1,
                    value2,
                    self.operator_type_map.get(a := op.type.name.upper()) or a,
                    (value1.line[1], value2.line[1]),
                    (value1.column[1], value2.column[1]),
                )
                del operators[i]
                del operands[i + 1]
                break
        return operands[0]

    def parse_type(self):
        self.expect_token_type(TokenType.Keyword)
        if self.ct.value == "VARCHAR":
            self.adv()
            self.expect_token_type(TokenType.LeftParen)
            self.adv()
            self.expect_token_type_and_value_type(TokenType.Number, int)
            length = self.ct.value
            self.adv()
            self.expect_token_type(TokenType.RightParen)
            return Node.Type.VarChar(length)
        elif self.ct.value == "DECIMAL":
            self.adv()
            self.expect_token_type(TokenType.LeftParen)
            self.adv()
            self.expect_token_type_and_value_type(TokenType.Number, int)
            digits = self.ct.value
            self.adv()
            self.expect_token_type(TokenType.Comma)
            self.adv()
            self.expect_token_type_and_value_type(TokenType.Number, int)
            precision = self.ct.value
            self.adv()
            self.expect_token_type(TokenType.RightParen)
            return Node.Type.Decimal(digits, precision)
        elif self.ct.value == "INT":
            return Node.Type.Int()
        elif self.ct.value == "BOOLEAN":
            return Node.Type.Boolean()

    def parse_create_table(self):
        line = self.ct.line
        column = self.ct.column
        self.adv()
        self.expect_token_type(TokenType.Identifier, TokenType.String)
        name = self.ct.value
        self.adv()
        self.expect_token_type(TokenType.LeftParen)
        self.adv()
        columns: dict[str, dict[str, Any]] = {}
        while self.ct and self.ct.type != TokenType.RightParen:
            column_name = self.ct.value
            info = {}
            self.adv()
            info["type"] = self.parse_type()
            self.adv()
            constraints = []
            while self.ct.type not in (
                TokenType.EOF,
                None,
                TokenType.Comma,
                TokenType.RightParen,
            ):
                self.expect_token_type(TokenType.Keyword, TokenType.Not)
                if self.ct.value == "PRIMARY":
                    self.adv()
                    self.expect_token(TokenType.Keyword, "KEY")
                    info["primary"] = True
                elif self.ct.value == "NOT":
                    self.adv()
                    self.expect_token_type(TokenType.Null)
                    constraints.append(("NOT_NULL",))
                elif self.ct.value == "CHECK":
                    self.adv()
                    self.expect_token_type(TokenType.LeftParen)
                    self.adv()
                    expr = self.parse_expression(ending=TokenType.RightParen)
                    constraints.append(("CHECK_EXPR", expr))
                elif self.ct.value == "UNIQUE":
                    constraints.append(("UNIQUE",))
                self.adv()
            info["constraints"] = constraints
            columns[column_name] = info
            if self.ct.type != TokenType.RightParen:
                self.adv()
        self.expect_token_type(TokenType.RightParen)
        self.adv()
        self.expect_token_type(TokenType.EOF, TokenType.Semicolon)
        return Node.CreateTable(
            name, columns, (line, self.ct.line), (column, self.ct.column)
        )

    def parse_create(self):
        self.adv()
        self.expect_token_type(TokenType.Keyword)
        if self.ct.value == "TABLE":
            return self.parse_create_table()

    def parse_select(self):
        line = self.ct.line
        column = self.ct.column
        to_select = self.parse_expression()
        return Node.Select(to_select, (line, self.ct.line), (column, self.ct.column))

    def parse_insert(self):
        line = self.ct.line
        column = self.ct.column
        self.adv()
        self.expect_token(TokenType.Keyword, "INTO")
        self.adv()
        self.expect_token_type(TokenType.Identifier, TokenType.String)
        table_name = self.ct.value
        self.adv()
        to_insert = None
        if self.ct.type == TokenType.LeftParen:
            to_insert = ()
            while self.ct.type != TokenType.RightParen:
                self.adv()
                to_insert += (
                    self.parse_expression(
                        ending=TokenType.Comma, altEndings=(TokenType.RightParen,)
                    ),
                )
        else:
            to_insert = self.parse_expression()
        self.adv()
        self.expect_token_type(TokenType.EOF, TokenType.Semicolon)
        return Node.Insert(
            table_name, to_insert, (line, self.ct.line), (column, self.ct.column)
        )

    def parse_drop_table(self, line: int, column: int) -> Node.DropTable:
        self.expect_token_type(TokenType.Identifier, TokenType.String)
        name = self.ct.value
        self.adv()
        self.expect_token_type(TokenType.EOF, TokenType.Semicolon)
        return Node.DropTable(name, (line, self.ct.line), (column, self.ct.column))

    def parse_drop(self):
        line = self.ct.line
        column = self.ct.line
        self.adv()
        self.expect_token_type(TokenType.Keyword)
        if self.ct.value == "TABLE":
            self.adv()
            return self.parse_drop_table(line, column)

    def parse(self) -> tuple[list[Node], ...]:
        extra_values: list[Any] = []
        while self.ct is not None and self.ct.type != TokenType.EOF:
            if self.ct.type == TokenType.Shebang:
                extra_values.append(self.parse_shebang(self.ct))
            elif self.ct.type == TokenType.Keyword:
                self.ast.append(self.keyword_handlers[self.ct.value]())
            else:
                self.ast.append(self.parse_expression())
            self.adv()
        return (self.ast, *extra_values)
