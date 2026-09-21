# Copyright (C) 2026 BasaltDev
# SPDX-License-Identifier: GPL-3.0-only

import json
import pathlib
import sys
from typing import Any

from . import visualizer
from .lexer import Lexer
from .parser import Node, Parser


class Interpreter:
    def __init__(self, query_path: pathlib.Path, db_path: pathlib.Path | None = None):
        with query_path.open(encoding="utf-8") as f:
            query_src = f.read()
        if db_path:
            self.db_path = db_path
            self.db_file = self.db_path.open("r+", encoding="utf-8")
        try:
            self.ast = Parser(Lexer(query_src)).parse()
        except Exception as e:
            if str(e) != "":
                print(f"Error: {e}")
            sys.exit(1)
        if len(self.ast) > 1:
            db_path = pathlib.Path(self.ast[1])  # type: ignore
            if not db_path.exists():
                print(f"Error: no such file `{db_path}`")
                sys.exit(1)
            self.db_path = db_path
            self.db_file = self.db_path.open("r+", encoding="utf-8")
            self.ast = self.ast[0]
        else:
            self.ast = self.ast[0]  # type: ignore
        self.pos = -1
        self.cn = None
        self.adv()
        self.db_json: dict[str, dict[str, Any]]
        self.read_db()
        self.env: dict[str, Any] = {}

    def read_db(self):
        try:
            self.db_file.seek(0)
            self.db_json = json.load(self.db_file)
        except json.decoder.JSONDecodeError:
            raise ValueError(f"could not read `{self.db_path}`", None, None) from None

    def write_db(self):
        self.db_file.seek(0)
        self.db_file.truncate()
        json.dump(self.db_json, self.db_file, ensure_ascii=False, separators=(",",":"))
        self.db_file.flush()

    def update_db_table(self, table: str, key: str, value: Any):
        self.db_json[table][key]["elements"].append(value)
        self.write_db()

    def update_db(self, key: str, value: Any):
        self.db_json[key] = value
        self.write_db()

    def adv(self):
        self.pos += 1
        self.cn = None if self.pos >= len(self.ast) else self.ast[self.pos]

    def resolve_literal(self, literal: Node.Literal):
        if literal.type == Node.LiteralType.Identifier:
            return self.env.get(literal.value)
        return literal.value

    def parse_expression(self, expr: Node.Expr | Node.Literal) -> Any:
        if isinstance(expr, Node.Literal):
            return self.resolve_literal(expr)
        rhs = self.parse_expression(expr.rhs)  # type: ignore
        if isinstance(expr, Node.UnExpr):
            if expr.op == "NEG":
                return -rhs
            elif expr.op == "NOT":
                return not rhs
        lhs = self.parse_expression(expr.lhs)  # type: ignore
        if isinstance(expr, Node.BinExpr):
            if expr.op == "+":
                return lhs + rhs
            elif expr.op == "-":
                return lhs - rhs
            elif expr.op == "*":
                return lhs * rhs
            elif expr.op == "/":
                if int in (type(lhs), type(rhs)):
                    return int(lhs // rhs)
                return lhs / rhs
            elif expr.op == "MOD":
                return lhs % rhs
            elif expr.op == "AND":
                return lhs and rhs
            elif expr.op == "OR":
                return lhs or rhs
            elif expr.op == "<":
                return lhs < rhs
            elif expr.op == ">":
                return lhs > rhs
            elif expr.op == "<=":
                return lhs <= rhs
            elif expr.op == ">=":
                return lhs >= rhs
        elif isinstance(expr, Node.TrinExpr):
            mhs = self.parse_expression(expr.mhs)
            if expr.op == "BETWEEN":
                return lhs >= mhs and lhs <= rhs

    def stringify_expression(self, expression: Node.Expr | Node.Literal) -> str:
        if isinstance(expression, Node.Literal):
            return str(expression.value)
        if isinstance(expression, Node.UnExpr):
            rhs = self.stringify_expression(expression.rhs)
            return f"{expression.op}{' ' if expression.op != '-' else ''}{rhs}"
        if isinstance(expression, Node.BinExpr):
            lhs = self.stringify_expression(expression.lhs)
            rhs = self.stringify_expression(expression.rhs)
            return f"{lhs} {expression.op} {rhs}"
        if isinstance(expression, Node.TrinExpr):
            lhs = self.stringify_expression(expression.lhs)
            mhs = self.stringify_expression(expression.mhs)
            rhs = self.stringify_expression(expression.rhs)
            return f"{lhs} {expression.op} {mhs} AND {rhs}"
        return ""

    def resolve_table_constraint(self, constraint: tuple[str, Node.Expr | Any]) -> str:
        if not constraint:
            return ""
        constraint_str = ""
        if constraint[0] == "CHECK_EXPR":
            constraint_str = f"CHECK {self.stringify_expression(constraint[1])}"
        else:
            constraint_str = constraint[0].replace("_", " ")
        return constraint_str

    def handle_create_table(self, node: Node.CreateTable):
        if node.name in self.db_json:
            raise ValueError(
                f"`{node.name}` is already a table", node.line, node.column
            )
        table_json: dict[str, dict[str, Any]] = {}
        primary_found = False
        for column, value in node.columns.items():
            col_type = value["type"].sqleon_format()
            if "primary" in value:
                if primary_found:
                    raise ValueError("cannot have more than 2 primary keys", node.line, node.column)
                primary_found = True
            constraints = [
                self.resolve_table_constraint(const) for const in value["constraints"]
            ]
            temp = value.copy()
            value.pop("type")
            value.pop("constraints")
            table_json[column] = {
                "type": col_type,
                **value,
                "elements": [],
                "constraints": [*constraints],
            }
            value = temp
        self.update_db(node.name, table_json)

    def handle_select(self, node: Node.Select) -> Any:
        if (
            isinstance(node.to_select, Node.Literal)
            and node.to_select.type == Node.LiteralType.Identifier
        ):
            table = self.db_json[node.to_select.value]
            return [(k, *v["elements"]) for k, v in table.items()]  # type: ignore
        else:
            return self.parse_expression(node.to_select)  # type: ignore

    def handle_insert(self, node: Node.Insert):
        if node.table_name not in self.db_json:
            raise ValueError(
                f"`{node.table_name}` is not a table", node.line, node.column
            )
        if isinstance(node.to_insert, tuple):
            to_insert = list(map(self.parse_expression, node.to_insert))
        else:
            to_insert = self.parse_expression(node.to_insert)
        table = self.db_json[node.table_name]
        self.env = {
            node.table_name: table,
            **{
                column: {"env_type": "column", "elements": col_value["elements"]}
                for column, col_value in table.items()
            },
        }
        for k, v in list(zip(table.keys(), to_insert, strict=True)):
            constraints = table[k]["constraints"]
            column_type = Node.Type.resolve_name(table[k]["type"])
            value_type = Node.Type.turn_value_into_type(v)
            if not value_type.matches_type(column_type):  # type: ignore
                raise ValueError(
                    f"value for `{k}` key in INSERT statement (of type {value_type.sqleon_format()}) does not match expected type ({column_type.sqleon_format()})",  # type: ignore
                    node.line,
                    node.column,
                )
            self.env[k] = v
            for constraint in constraints:
                if constraint == "UNIQUE":
                    if v in table[k]["elements"]:
                        raise ValueError(
                            f"value for key `{k}` in INSERT statement (`{v}`) must be UNIQUE",
                            node.line,
                            node.column,
                        )
                elif constraint == "NOT NULL":
                    if v is None:
                        raise ValueError(
                            f"value for key `{k}` in INSERT statement must not be NULL",
                            node.line,
                            node.column,
                        )
                elif constraint.startswith("CHECK"):
                    constraint = constraint[6:]
                    expr = Parser(Lexer(constraint)).parse_expression()
                    true = self.parse_expression(expr)
                    if not true:
                        raise ValueError(
                            f"value for `{k}` key in INSERT statement does not pass custom check constraint (`{constraint}`)",
                            node.line,
                            node.column,
                        )
            self.update_db_table(node.table_name, k, v)

    def handle_droptable(self, node: Node.DropTable):
        if node.to_drop not in self.db_json:
            raise ValueError(f"`{node.to_drop}` is not an existing table", node.line, node.column)
        del self.db_json[node.to_drop]
        self.write_db()

    def interpret(self):
        error: Exception | None = None
        try:
            while self.cn is not None:
                if isinstance(self.cn, Node.CreateTable):
                    self.handle_create_table(self.cn)
                    visualizer.visualize({self.cn.name: self.db_json[self.cn.name]})
                elif isinstance(self.cn, Node.Select):
                    value: list[Any] | Any = self.handle_select(self.cn)
                    if isinstance(value, list) and all(isinstance(v, tuple) for v in value):  # type: ignore
                        visualizer.visualize({self.cn.to_select.value: self.db_json[self.cn.to_select.value]})  # type: ignore
                    else:
                        print(value)  # type: ignore
                elif isinstance(self.cn, Node.Insert):
                    self.handle_insert(self.cn)
                    visualizer.visualize({self.cn.table_name: self.db_json[self.cn.table_name]})
                elif isinstance(self.cn, Node.DropTable):
                    self.handle_droptable(self.cn)
                self.adv()
            if not self.db_file.closed:
                self.write_db()
                self.db_file.close()
        except Exception as e:
            error = e
        if not self.db_file.closed:
            self.write_db()
            self.db_file.close()
        if error:
            if len(error.args) != 3:
                print(f"Error: {error}")
                sys.exit(1)
            print(
                f"Error (line {error.args[1][0]}-{error.args[1][1]}, column {error.args[2][0]}-{error.args[2][1]}): {error.args[0]}"
            )
            sys.exit(1)
