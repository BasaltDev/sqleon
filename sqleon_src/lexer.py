# Copyright (C) 2026 BasaltDev
# SPDX-License-Identifier: GPL-3.0-only

# type: ignore
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum, auto
from typing import Any, ClassVar

from . import error


class TokenType(Enum):
    Keyword = auto()
    Identifier = auto()
    Number = auto()
    String = auto()
    Boolean = auto()
    Null = auto()

    LeftParen = auto()
    RightParen = auto()

    Period = auto()
    Comma = auto()
    Semicolon = auto()

    Plus = auto()
    Minus = auto()
    Star = auto()
    Slash = auto()
    Mod = auto()

    Equal = auto()
    LessThan = auto()
    LessThanEqual = auto()
    GreaterThan = auto()
    GreaterThanEqual = auto()
    NotEqual = auto()

    Is = auto()
    Between = auto()
    Or = auto()
    And = auto()
    Not = auto()

    Shebang = auto()
    EOF = auto()


class TokenTypeGroups:
    Operators = (
        TokenType.Plus,
        TokenType.Minus,
        TokenType.Star,
        TokenType.Slash,
        TokenType.Mod,
        TokenType.Equal,
        TokenType.LessThan,
        TokenType.LessThanEqual,
        TokenType.GreaterThan,
        TokenType.GreaterThanEqual,
        TokenType.NotEqual,
        TokenType.Is,
        TokenType.Between,
        TokenType.Not,
        TokenType.Or,
        TokenType.And,
    )
    LowerArithmeticOperators = (
        TokenType.Plus,
        TokenType.Minus,
    )
    HigherArithmeticOperators = (TokenType.Star, TokenType.Slash, TokenType.Mod)
    EqualityOperators = (TokenType.Equal, TokenType.NotEqual)
    ComparisonOperators = (
        TokenType.LessThan,
        TokenType.LessThanEqual,
        TokenType.GreaterThan,
        TokenType.GreaterThanEqual,
    )
    UnaryOperators: ClassVar[dict[TokenType, str]] = {
        TokenType.Minus: "NEG",
        TokenType.Not: "NOT",
    }


@dataclass(frozen=True)
class Token:
    type: TokenType | str
    value: str | int | Decimal | bool | None
    line: int
    column: int

    def __eq__(self, other: Any):
        pass


class Lexer:
    keywords = {  # noqa: RUF012
        "CREATE": TokenType.Keyword,
        "TABLE": TokenType.Keyword,
        "SELECT": TokenType.Keyword,
        "INSERT": TokenType.Keyword,
        "INTO": TokenType.Keyword,
        "CHECK": TokenType.Keyword,
        "DROP": TokenType.Keyword,
        "IS": TokenType.Is,
        "BETWEEN": TokenType.Between,
        "NOT": TokenType.Not,
        "OR": TokenType.Or,
        "AND": TokenType.And,
        "INT": TokenType.Keyword,
        "DECIMAL": TokenType.Keyword,
        "BOOLEAN": TokenType.Keyword,
        "VARCHAR": TokenType.Keyword,
        "PRIMARY": TokenType.Keyword,
        "KEY": TokenType.Keyword,
        "UNIQUE": TokenType.Keyword,
        "MOD": TokenType.Mod,
    }
    char_map: ClassVar = {
        "(": TokenType.LeftParen,
        ")": TokenType.RightParen,
        ".": TokenType.Period,
        ",": TokenType.Comma,
        ";": TokenType.Semicolon,
        "+": TokenType.Plus,
        "-": TokenType.Minus,
        "*": TokenType.Star,
        "/": TokenType.Slash,
        "%": TokenType.Mod,
        "<": TokenType.LessThan,
        ">": TokenType.GreaterThan,
        "<=": TokenType.LessThanEqual,
        ">=": TokenType.GreaterThanEqual,
        "=": TokenType.Equal,
        "!=": TokenType.NotEqual,
        "<>": TokenType.NotEqual,
    }

    def __init__(self, src: str):
        self.src = src
        self.pos = -1
        self.cc: str | None = None
        self.line = 1
        self.col = 0
        self.adv()
        self.tokens: list[Token] = []

    def adv(self, amt=1) -> str | None:
        self.pos += amt
        self.col += amt
        self.cc = None if self.pos >= len(self.src) else self.src[self.pos]
        if self.cc == "\n":
            self.line += 1
            self.col = 0

    def peek(self, amt: int = 1) -> str | None:
        return None if self.pos + amt >= len(self.src) else self.src[self.pos + amt]

    def make_token(
        self,
        ttype: TokenType,
        value: str | int | Decimal | bool | None = None,
        line: int = 0,
        column: int = 0,
    ) -> None:
        self.tokens.append(Token(ttype, value, line, column))

    def lex(self) -> list[Token]:
        comment = False
        while self.cc:
            if comment:
                if self.cc == "\n":
                    comment = False
                self.adv()
                continue
            if self.cc in " \t\n\r":
                self.adv()
                continue
            if self.cc == "-" and self.peek() == "-":
                if self.peek(2) == "!":
                    self.adv(3)
                    column = self.col
                    out = self.cc
                    while self.peek() not in (None, "\n"):
                        out += self.peek()
                        self.adv()
                    self.make_token(TokenType.Shebang, out, self.line, column)
                else:
                    comment = 1
                self.adv()
                continue
            if self.cc.isalpha() or self.cc == "_":
                out: str | bool = self.cc
                line = self.line
                column = self.col
                while self.peek() and (self.peek().isalpha() or self.peek() == "_"):
                    out += self.peek()
                    self.adv()
                out = out.upper()
                ttype = TokenType.Identifier
                if out in self.keywords:
                    ttype = self.keywords[out]
                elif out in ("TRUE", "FALSE", "UNKNOWN"):
                    ttype = TokenType.Boolean
                    if out != "UNKNOWN":
                        out = True if out == "TRUE" else False
                elif out == "NULL":
                    ttype = TokenType.Null
                    out = None
                self.make_token(ttype, out, line, column)
            elif self.cc.isdigit():
                out: str | int | Decimal = self.cc
                line = self.line
                column = self.col
                while self.peek() and (self.peek().isdigit() or self.peek() == "."):
                    out += self.peek()
                    if out.count(".") > 1:
                        error.error("unexpected floating point", (self.line, self.col))
                    self.adv()
                out = Decimal(out) if "." in out else int(out)
                self.make_token(TokenType.Number, out, line, column)
            elif self.cc in "'\"":
                ending = self.cc
                line = self.line
                column = self.col
                out = ""
                while self.peek() and self.peek() != ending:
                    out += self.peek()
                    self.adv()
                if self.peek() != ending:
                    error.error("expected quote", (self.line, self.col))
                self.adv()
                self.make_token(TokenType.String, out, line, column)
            elif self.peek() and self.cc + self.peek() in self.char_map:
                self.make_token(
                    self.char_map[self.cc + self.peek()],
                    line=self.line,
                    column=self.col,
                )
                self.adv()
            elif self.cc in self.char_map:
                self.make_token(self.char_map[self.cc], line=self.line, column=self.col)
            self.adv()
        self.make_token(TokenType.EOF, line=self.line, column=self.col)
        return self.tokens
