"""
SQL Generator

Converts logical plan back to SQL string.
"""

from typing import Dict, List, Any, Optional, Set, Tuple
from logical_plan import (
    LogicalOperator, LogicalScan, LogicalProject, LogicalFilter,
    LogicalJoin, LogicalAggregate, LogicalSort, LogicalLimit
)
from sql_optimizer import (
    Column, BinaryExpression, BinaryOp, Literal, Table
)


class SQLGenerator:
    """Converts a logical plan back to SQL"""
    
    def generate(self, plan: LogicalOperator) -> str:
        """Generate SQL from a logical plan"""
        # We'll use a recursive approach to build SQL subqueries as needed
        return self._generate_sql(plan)
    
    def _generate_sql(self, op: LogicalOperator) -> str:
        """Generate SQL recursively"""
        if isinstance(op, LogicalProject):
            # For projections, we need to identify the base query
            base_query = self._generate_base_query(op.input_op)
            
            # Add columns
            columns_str = ", ".join(str(col) for col in op.columns)
            
            return f"SELECT {columns_str}\n{base_query}"
        
        # This should not happen in our implementation,
        # as the top level should always be a projection
        raise ValueError("Expected LogicalProject at the top level")
    
    def _generate_base_query(self, op: LogicalOperator) -> str:
        """Generate the base query (FROM, WHERE, etc.)"""
        if isinstance(op, LogicalScan):
            # Simple scan operation
            table_name = op.table.name
            if op.table.alias:
                table_name += f" AS {op.table.alias}"
            return f"FROM {table_name}"
        
        elif isinstance(op, LogicalFilter):
            # Filter operation (WHERE)
            base_query = self._generate_base_query(op.input_op)
            condition_str = self._format_expression(op.condition)
            
            # Check if the base query already has a WHERE clause
            if "WHERE" in base_query:
                # If it does, we need to add our condition with AND
                where_index = base_query.find("WHERE")
                # Find the next clause (GROUP BY, ORDER BY, LIMIT)
                next_clause_keywords = ["GROUP BY", "ORDER BY", "LIMIT"]
                next_clause_indexes = [base_query.find(keyword) for keyword in next_clause_keywords]
                next_clause_indexes = [idx for idx in next_clause_indexes if idx > 0]
                
                if next_clause_indexes:
                    # Insert before the next clause
                    insert_position = min(next_clause_indexes)
                    return (
                        f"{base_query[:insert_position]}AND {condition_str}\n"
                        f"{base_query[insert_position:]}"
                    )
                else:
                    # No next clause, add at the end
                    return f"{base_query} AND {condition_str}"
            else:
                # Add a new WHERE clause
                return f"{base_query}\nWHERE {condition_str}"
        
        elif isinstance(op, LogicalJoin):
            # Join operation
            left_base = self._determine_join_base(op.left)
            right_base = self._determine_join_base(op.right)
            
            # If left_base is a simple table scan, we can use it as the FROM clause
            # Otherwise, we need to create a subquery
            if isinstance(op.left, LogicalScan):
                from_clause = left_base
            else:
                from_clause = f"FROM ({self._generate_sql(self._wrap_as_projection(op.left))}) AS derived_left"
            
            # Add the join
            join_type = op.join_type.value
            
            if isinstance(op.right, LogicalScan):
                table_name = op.right.table.name
                if op.right.table.alias:
                    table_name += f" AS {op.right.table.alias}"
                join_clause = f"{join_type} JOIN {table_name}"
            else:
                subquery = self._generate_sql(self._wrap_as_projection(op.right))
                join_clause = f"{join_type} JOIN ({subquery}) AS derived_right"
            
            # Add join condition
            if op.condition:
                condition_str = self._format_expression(op.condition)
                join_clause += f" ON {condition_str}"
            
            return f"{from_clause}\n{join_clause}"
        
        elif isinstance(op, LogicalAggregate):
            # Group by operation
            base_query = self._generate_base_query(op.input_op)
            columns_str = ", ".join(str(col) for col in op.group_by_columns)
            
            return f"{base_query}\nGROUP BY {columns_str}"
        
        elif isinstance(op, LogicalSort):
            # Order by operation
            base_query = self._generate_base_query(op.input_op)
            sort_items = [f"{col} {dir}" for col, dir in zip(op.columns, op.directions)]
            sort_str = ", ".join(sort_items)
            
            return f"{base_query}\nORDER BY {sort_str}"
        
        elif isinstance(op, LogicalLimit):
            # Limit operation
            base_query = self._generate_base_query(op.input_op)
            return f"{base_query}\nLIMIT {op.limit}"
        
        # This is a fallback - in practice, we would handle all operator types
        raise ValueError(f"Unsupported operator type: {type(op)}")
    
    def _determine_join_base(self, op: LogicalOperator) -> str:
        """Determine the base for a join operation"""
        if isinstance(op, LogicalScan):
            table_name = op.table.name
            if op.table.alias:
                table_name += f" AS {op.table.alias}"
            return f"FROM {table_name}"
        
        # For complex operations, we'd need to create a subquery
        # This simplified version just returns a placeholder
        return "FROM derived_table"
    
    def _wrap_as_projection(self, op: LogicalOperator) -> LogicalProject:
        """Wrap an operator in a projection if necessary"""
        if isinstance(op, LogicalProject):
            return op
        
        # Determine columns from the operator
        # This is a simplified version - in practice, we would analyze
        # which columns are available from this operator
        columns = [Column(name="*")]
        
        return LogicalProject(input_op=op, columns=columns)
    
    def _format_expression(self, expr: BinaryExpression) -> str:
        """Format a binary expression as SQL"""
        left_str = self._format_operand(expr.left)
        right_str = self._format_operand(expr.right)
        
        return f"{left_str} {expr.op.value} {right_str}"
    
    def _format_operand(self, operand: Any) -> str:
        """Format an operand as SQL"""
        if isinstance(operand, Column):
            col_str = operand.name
            if operand.table:
                col_str = f"{operand.table}.{col_str}"
            return col_str
        
        elif isinstance(operand, Literal):
            if operand.type == "string":
                return f"'{operand.value}'"
            return str(operand.value)
        
        elif isinstance(operand, BinaryExpression):
            return f"({self._format_expression(operand)})"
        
        # Default case
        return str(operand)


# Example usage
if __name__ == "__main__":
    from sql_parser import SQLParser
    from logical_plan import ASTToLogicalConverter
    from optimizer import Optimizer
    
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
        AND b.active = TRUE
    ORDER BY 
        a.id DESC
    LIMIT 100
    """
    
    print("Original SQL:")
    print(sql)
    
    # Parse the SQL
    parser = SQLParser(sql)
    ast = parser.parse()
    
    # Convert to logical plan
    converter = ASTToLogicalConverter()
    logical_plan = converter.convert(ast)
    
    # Optimize the plan
    optimizer = Optimizer()
    optimized_plan = optimizer.optimize(logical_plan)
    
    # Generate optimized SQL
    generator = SQLGenerator()
    optimized_sql = generator.generate(optimized_plan)
    
    print("\nOptimized SQL:")
    print(optimized_sql)