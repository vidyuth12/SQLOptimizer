"""
SQL Parser

A simple recursive descent parser for SQL SELECT statements.
"""

import re
from typing import List, Optional, Dict, Any, Tuple
from sql_optimizer import (
    Select, From, Where, Column, Table, Join, JoinType,
    BinaryExpression, BinaryOp, Literal, OrderBy, GroupBy
)


class SQLParser:
    def __init__(self, sql: str):
        self.sql = sql.strip()
        self.tokens = self._tokenize(self.sql)
        self.pos = 0

    def _tokenize(self, sql: str) -> List[str]:
        # A very basic tokenizer
        # Replace newlines with spaces
        sql = sql.replace('\n', ' ')
        
        # Ensure spaces around operators and punctuation
        for symbol in ['=', '<', '>', '!', ',', '(', ')', '.']:
            sql = sql.replace(symbol, f' {symbol} ')
        
        # Handle special cases like !=, <=, >=
        sql = sql.replace(' ! = ', ' != ')
        sql = sql.replace(' < = ', ' <= ')
        sql = sql.replace(' > = ', ' >= ')
        
        # Split by whitespace and filter out empty tokens
        return [token for token in sql.split() if token]

    def _peek(self) -> str:
        if self.pos >= len(self.tokens):
            return ""
        return self.tokens[self.pos]

    def _consume(self) -> str:
        token = self._peek()
        self.pos += 1
        return token

    def _expect(self, expected: str) -> str:
        token = self._consume()
        if token.upper() != expected.upper():
            raise ValueError(f"Expected '{expected}', got '{token}'")
        return token

    def _match(self, expected: str) -> bool:
        if self._peek().upper() == expected.upper():
            self._consume()
            return True
        return False

    def parse(self) -> Select:
        """Parse a SQL SELECT statement"""
        return self._parse_select()

    def _parse_select(self) -> Select:
        self._expect("SELECT")
        columns = self._parse_columns()
        
        from_clause = self._parse_from()
        where_clause = self._parse_where() if self._peek().upper() == "WHERE" else None
        group_by = self._parse_group_by() if self._peek().upper() == "GROUP" else None
        order_by = self._parse_order_by() if self._peek().upper() == "ORDER" else None
        
        limit = None
        if self._peek().upper() == "LIMIT":
            self._consume()  # Consume "LIMIT"
            limit = int(self._consume())
        
        return Select(
            columns=columns,
            from_clause=from_clause,
            where_clause=where_clause,
            group_by=group_by,
            order_by=order_by,
            limit=limit
        )

    def _parse_columns(self) -> List[Column]:
        columns = []
        
        while True:
            col_name = self._consume()
            table = None
            
            # Check if column has table qualifier (table.column)
            if self._peek() == ".":
                self._consume()  # Consume "."
                table = col_name
                col_name = self._consume()
            
            alias = None
            if self._peek().upper() == "AS":
                self._consume()  # Consume "AS"
                alias = self._consume()
            
            columns.append(Column(name=col_name, table=table, alias=alias))
            
            if self._peek() != ",":
                break
                
            self._consume()  # Consume ","
        
        return columns

    def _parse_from(self) -> From:
        self._expect("FROM")
        table_name = self._consume()
        alias = None
        
        if self._peek().upper() == "AS":
            self._consume()  # Consume "AS"
            alias = self._consume()
        elif not (self._peek().upper() in ["JOIN", "WHERE", "GROUP", "ORDER", "LIMIT"] or self._peek() == ""):
            # Implicit alias
            alias = self._consume()
            
        table = Table(name=table_name, alias=alias)
        joins = []
        
        while self._peek().upper() in ["JOIN", "INNER", "LEFT", "RIGHT", "FULL"]:
            join_type = JoinType.INNER
            
            if self._peek().upper() == "LEFT":
                self._consume()
                join_type = JoinType.LEFT
            elif self._peek().upper() == "RIGHT":
                self._consume()
                join_type = JoinType.RIGHT
            elif self._peek().upper() == "FULL":
                self._consume()
                join_type = JoinType.FULL
            elif self._peek().upper() == "INNER":
                self._consume()
                join_type = JoinType.INNER
                
            self._expect("JOIN")
            join_table_name = self._consume()
            join_alias = None
            
            if self._peek().upper() == "AS":
                self._consume()  # Consume "AS"
                join_alias = self._consume()
            elif not (self._peek().upper() in ["ON", "WHERE", "GROUP", "ORDER", "LIMIT"] or self._peek() == ""):
                # Implicit alias
                join_alias = self._consume()
                
            join_table = Table(name=join_table_name, alias=join_alias)
            
            condition = None
            if self._match("ON"):
                condition = self._parse_expression()
                
            joins.append(Join(table=join_table, condition=condition, join_type=join_type))
        
        return From(table=table, joins=joins)

    def _parse_where(self) -> Where:
        self._expect("WHERE")
        condition = self._parse_expression()
        return Where(condition=condition)

    def _parse_group_by(self) -> GroupBy:
        self._expect("GROUP")
        self._expect("BY")
        columns = []
        
        while True:
            col_name = self._consume()
            table = None
            
            if self._peek() == ".":
                self._consume()  # Consume "."
                table = col_name
                col_name = self._consume()
                
            columns.append(Column(name=col_name, table=table))
            
            if self._peek() != ",":
                break
                
            self._consume()  # Consume ","
            
        return GroupBy(columns=columns)

    def _parse_order_by(self) -> OrderBy:
        self._expect("ORDER")
        self._expect("BY")
        columns = []
        directions = []
        
        while True:
            col_name = self._consume()
            table = None
            
            if self._peek() == ".":
                self._consume()  # Consume "."
                table = col_name
                col_name = self._consume()
                
            columns.append(Column(name=col_name, table=table))
            
            # Check for direction
            if self._peek().upper() in ["ASC", "DESC"]:
                directions.append(self._consume().upper())
            else:
                directions.append("ASC")  # Default
            
            if self._peek() != ",":
                break
                
            self._consume()  # Consume ","
            
        return OrderBy(columns=columns, directions=directions)

    def _parse_expression(self) -> BinaryExpression:
        left = self._parse_term()
        
        while self._peek().upper() in ["AND", "OR"]:
            op_str = self._consume().upper()
            op = BinaryOp.AND if op_str == "AND" else BinaryOp.OR
            right = self._parse_term()
            left = BinaryExpression(left=left, op=op, right=right)
            
        return left

    def _parse_term(self) -> Any:
        if self._peek() == "(":
            self._consume()  # Consume "("
            expr = self._parse_expression()
            self._expect(")")
            return expr
            
        left = self._parse_factor()
        
        if self._peek() in ["=", "!=", "<", ">", "<=", ">="]:
            op_str = self._consume()
            
            if op_str == "=":
                op = BinaryOp.EQ
            elif op_str == "!=":
                op = BinaryOp.NEQ
            elif op_str == "<":
                op = BinaryOp.LT
            elif op_str == ">":
                op = BinaryOp.GT
            elif op_str == "<=":
                op = BinaryOp.LTE
            elif op_str == ">=":
                op = BinaryOp.GTE
            else:
                raise ValueError(f"Unknown operator: {op_str}")
                
            right = self._parse_factor()
            return BinaryExpression(left=left, op=op, right=right)
            
        return left

    def _parse_factor(self) -> Any:
        token = self._consume()
        
        # Check if it's a number
        if token.isdigit() or (token[0] == '-' and token[1:].isdigit()):
            return Literal(value=int(token), type="number")
            
        # Check if it's a string literal
        if token.startswith("'") and token.endswith("'"):
            return Literal(value=token[1:-1], type="string")
            
        # Check if it's a column reference with table
        if self._peek() == ".":
            self._consume()  # Consume "."
            column_name = self._consume()
            return Column(name=column_name, table=token)
            
        # Assume it's a column name
        return Column(name=token)


# Example usage
if __name__ == "__main__":
    sql = """
    SELECT 
        a.id, 
        b.name 
    FROM 
        table_a AS a 
    JOIN 
        table_b b 
    ON 
        a.id = b.id 
    WHERE 
        a.value > 10 
    ORDER BY 
        a.id DESC, 
        b.name ASC
    LIMIT 100
    """
    
    parser = SQLParser(sql)
    ast = parser.parse()
    print(ast)