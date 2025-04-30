"""
SQL Optimizer

A Python library for parsing, optimizing, and generating SQL queries.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Union, Dict, Any
from enum import Enum


class ASTNode:
    """Base class for all AST nodes"""
    pass


class JoinType(Enum):
    INNER = "INNER"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    FULL = "FULL"


class BinaryOp(Enum):
    EQ = "="
    NEQ = "!="
    LT = "<"
    LTE = "<="
    GT = ">"
    GTE = ">="
    AND = "AND"
    OR = "OR"
    ADD = "+"
    SUB = "-"
    MUL = "*"
    DIV = "/"


@dataclass
class Column(ASTNode):
    name: str
    table: Optional[str] = None
    alias: Optional[str] = None

    def __str__(self) -> str:
        col_str = f"{self.table}.{self.name}" if self.table else self.name
        if self.alias:
            col_str += f" AS {self.alias}"
        return col_str


@dataclass
class Table(ASTNode):
    name: str
    alias: Optional[str] = None

    def __str__(self) -> str:
        table_str = self.name
        if self.alias:
            table_str += f" AS {self.alias}"
        return table_str


@dataclass
class BinaryExpression(ASTNode):
    left: Any  # Can be a Column, Literal, or another Expression
    op: BinaryOp
    right: Any

    def __str__(self) -> str:
        return f"({self.left} {self.op.value} {self.right})"


@dataclass
class Literal(ASTNode):
    value: Any
    type: str = "string"  # string, number, boolean, null

    def __str__(self) -> str:
        if self.type == "string":
            return f"'{self.value}'"
        return str(self.value)


@dataclass
class Join(ASTNode):
    table: Table
    condition: Optional[BinaryExpression] = None
    join_type: JoinType = JoinType.INNER

    def __str__(self) -> str:
        join_str = f"{self.join_type.value} JOIN {self.table}"
        if self.condition:
            join_str += f" ON {self.condition}"
        return join_str


@dataclass
class From(ASTNode):
    table: Table
    joins: List[Join] = field(default_factory=list)

    def __str__(self) -> str:
        from_str = f"FROM {self.table}"
        if self.joins:
            join_strs = [str(join) for join in self.joins]
            from_str += " " + " ".join(join_strs)
        return from_str


@dataclass
class Where(ASTNode):
    condition: BinaryExpression

    def __str__(self) -> str:
        return f"WHERE {self.condition}"


@dataclass
class OrderBy(ASTNode):
    columns: List[Column]
    directions: List[str] = field(default_factory=lambda: ["ASC"])

    def __str__(self) -> str:
        if len(self.directions) < len(self.columns):
            self.directions.extend(["ASC"] * (len(self.columns) - len(self.directions)))
        
        order_items = [f"{col} {dir}" for col, dir in zip(self.columns, self.directions)]
        return f"ORDER BY {', '.join(order_items)}"


@dataclass
class GroupBy(ASTNode):
    columns: List[Column]

    def __str__(self) -> str:
        return f"GROUP BY {', '.join(map(str, self.columns))}"


@dataclass
class Select(ASTNode):
    columns: List[Column]
    from_clause: From
    where_clause: Optional[Where] = None
    group_by: Optional[GroupBy] = None
    order_by: Optional[OrderBy] = None
    limit: Optional[int] = None

    def __str__(self) -> str:
        query = f"SELECT {', '.join(map(str, self.columns))}\n"
        query += f"{self.from_clause}\n"
        
        if self.where_clause:
            query += f"{self.where_clause}\n"
        
        if self.group_by:
            query += f"{self.group_by}\n"
        
        if self.order_by:
            query += f"{self.order_by}\n"
        
        if self.limit is not None:
            query += f"LIMIT {self.limit}"
            
        return query


# Example usage
if __name__ == "__main__":
    # Example: SELECT a.id, b.name FROM table_a a JOIN table_b b ON a.id = b.id WHERE a.value > 10
    query = Select(
        columns=[
            Column(name="id", table="a"),
            Column(name="name", table="b")
        ],
        from_clause=From(
            table=Table(name="table_a", alias="a"),
            joins=[
                Join(
                    table=Table(name="table_b", alias="b"),
                    condition=BinaryExpression(
                        left=Column(name="id", table="a"),
                        op=BinaryOp.EQ,
                        right=Column(name="id", table="b")
                    )
                )
            ]
        ),
        where_clause=Where(
            condition=BinaryExpression(
                left=Column(name="value", table="a"),
                op=BinaryOp.GT,
                right=Literal(value=10, type="number")
            )
        )
    )
    
    print(query)