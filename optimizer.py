"""
SQL Optimizer

Implementation of optimization rules and the optimizer engine.
"""

from typing import List, Dict, Set, Optional, Any, Tuple
from dataclasses import dataclass
from sql_optimizer import (
    ASTNode, Column, BinaryExpression, BinaryOp, Literal, Table
)
from logical_plan import (
    LogicalOperator, LogicalScan, LogicalProject, LogicalFilter,
    LogicalJoin, LogicalAggregate, LogicalSort, LogicalLimit
)

from typing import List, Dict, Set, Optional, Any
from dataclasses import dataclass
from sql_optimizer import (
    ASTNode, Column, BinaryExpression, BinaryOp, Literal, Table
)
from logical_plan import (
    LogicalOperator, LogicalScan, LogicalProject, LogicalFilter,
    LogicalJoin, LogicalAggregate, LogicalSort, LogicalLimit
)


class OptimizationRule:
    """Base class for all optimization rules"""
    
    def apply(self, plan: LogicalOperator) -> LogicalOperator:
        """Apply this rule to the logical plan"""
        raise NotImplementedError("Subclasses must implement apply()")


class PredicatePushdown(OptimizationRule):
    """Push filter predicates down as close as possible to the data source"""
    
    def apply(self, plan: LogicalOperator) -> LogicalOperator:
        """Apply predicate pushdown to the logical plan"""
        return self._apply_recursive(plan)
    
    def _apply_recursive(self, op: LogicalOperator) -> LogicalOperator:
        """Recursively apply predicate pushdown"""
        if isinstance(op, LogicalFilter):
            # Push the filter through its input
            pushed_input = self._push_filter(op.condition, op.input_op)
            
            # If the filter was completely pushed down, return the result
            # Otherwise, keep the filter but with optimized input
            if isinstance(pushed_input, LogicalFilter) and pushed_input.condition == op.condition:
                # The filter couldn't be pushed completely, but its input may have been optimized
                return LogicalFilter(
                    input_op=self._apply_recursive(pushed_input.input_op),
                    condition=op.condition
                )
            else:
                # The filter was at least partially pushed down
                return self._apply_recursive(pushed_input)
        
        elif isinstance(op, LogicalProject):
            # Optimize the input
            optimized_input = self._apply_recursive(op.input_op)
            return LogicalProject(input_op=optimized_input, columns=op.columns)
        
        elif isinstance(op, LogicalJoin):
            # Optimize both sides of the join
            optimized_left = self._apply_recursive(op.left)
            optimized_right = self._apply_recursive(op.right)
            return LogicalJoin(
                left=optimized_left,
                right=optimized_right,
                condition=op.condition,
                join_type=op.join_type
            )
        
        elif isinstance(op, LogicalAggregate):
            # Optimize the input
            optimized_input = self._apply_recursive(op.input_op)
            return LogicalAggregate(
                input_op=optimized_input,
                group_by_columns=op.group_by_columns,
                aggregate_expressions=op.aggregate_expressions
            )
        
        elif isinstance(op, LogicalSort):
            # Optimize the input
            optimized_input = self._apply_recursive(op.input_op)
            return LogicalSort(
                input_op=optimized_input,
                columns=op.columns,
                directions=op.directions
            )
        
        elif isinstance(op, LogicalLimit):
            # Optimize the input
            optimized_input = self._apply_recursive(op.input_op)
            return LogicalLimit(input_op=optimized_input, limit=op.limit)
        
        # Base case: no optimization for scan
        return op
    
    def _push_filter(self, condition: BinaryExpression, op: LogicalOperator) -> LogicalOperator:
        """Try to push a filter condition down through an operator"""
        if isinstance(op, LogicalProject):
            # We can push the filter through the projection, but we need to
            # ensure the filter only references columns available after projection
            # For simplicity, we'll assume this is possible for now
            pushed_input = self._push_filter(condition, op.input_op)
            return LogicalProject(input_op=pushed_input, columns=op.columns)
        
        elif isinstance(op, LogicalFilter):
            # Combine filters when possible using AND
            combined_condition = BinaryExpression(
                left=op.condition,
                op=BinaryOp.AND,
                right=condition
            )
            return LogicalFilter(
                input_op=op.input_op,
                condition=combined_condition
            )
        
        elif isinstance(op, LogicalJoin):
            # Try to push down to each side based on referenced tables
            left_tables = self._get_tables_from_operator(op.left)
            right_tables = self._get_tables_from_operator(op.right)
            
            # Check which tables the condition references
            condition_tables = self._get_tables_from_condition(condition)
            
            # If condition only references left tables, push to left
            if condition_tables.issubset(left_tables):
                return LogicalJoin(
                    left=self._push_filter(condition, op.left),
                    right=op.right,
                    condition=op.condition,
                    join_type=op.join_type
                )
            
            # If condition only references right tables, push to right
            if condition_tables.issubset(right_tables):
                return LogicalJoin(
                    left=op.left,
                    right=self._push_filter(condition, op.right),
                    condition=op.condition,
                    join_type=op.join_type
                )
            
            # Otherwise, keep the filter above the join
            return LogicalFilter(input_op=op, condition=condition)
        
        # For other operators, we can't push the filter down
        return LogicalFilter(input_op=op, condition=condition)
    
    def _get_tables_from_operator(self, op: LogicalOperator) -> Set[str]:
        """Get the set of table names accessible from this operator"""
        if isinstance(op, LogicalScan):
            return {op.table.alias or op.table.name}
        
        elif isinstance(op, LogicalProject):
            return self._get_tables_from_operator(op.input_op)
        
        elif isinstance(op, LogicalFilter):
            return self._get_tables_from_operator(op.input_op)
        
        elif isinstance(op, LogicalJoin):
            left_tables = self._get_tables_from_operator(op.left)
            right_tables = self._get_tables_from_operator(op.right)
            return left_tables.union(right_tables)
        
        elif isinstance(op, LogicalAggregate):
            return self._get_tables_from_operator(op.input_op)
        
        elif isinstance(op, LogicalSort):
            return self._get_tables_from_operator(op.input_op)
        
        elif isinstance(op, LogicalLimit):
            return self._get_tables_from_operator(op.input_op)
        
        return set()
    
    def _get_tables_from_condition(self, condition: BinaryExpression) -> Set[str]:
        """Get the set of table names referenced in a condition"""
        tables = set()
        
        # Extract tables from left side
        if isinstance(condition.left, Column) and condition.left.table:
            tables.add(condition.left.table)
        elif isinstance(condition.left, BinaryExpression):
            tables.update(self._get_tables_from_condition(condition.left))
        
        # Extract tables from right side
        if isinstance(condition.right, Column) and condition.right.table:
            tables.add(condition.right.table)
        elif isinstance(condition.right, BinaryExpression):
            tables.update(self._get_tables_from_condition(condition.right))
        
        return tables


class ProjectionPruning(OptimizationRule):
    """Prune unnecessary columns from projections"""
    
    def apply(self, plan: LogicalOperator) -> LogicalOperator:
        """Apply projection pruning to the logical plan"""
        # First, identify the columns needed at the top level
        required_columns = self._get_required_columns(plan)
        
        # Then propagate these requirements down the tree
        return self._prune_projections(plan, required_columns)
    
    def _get_required_columns(self, op: LogicalOperator) -> Set[Tuple[str, str]]:
        """Get the set of columns required by this operation and its ancestors"""
        if isinstance(op, LogicalProject):
            # Only columns in the final projection are required
            return {(col.table, col.name) for col in op.columns if col.table is not None}
        
        # For other operators, check their inputs
        # This is a simplified implementation - in a real optimizer, we'd need to
        # analyze which columns are actually needed for each operation
        return set()
    
    def _prune_projections(self, op: LogicalOperator, required_columns: Set[Tuple[str, str]]) -> LogicalOperator:
        """Prune unnecessary columns from projections"""
        # This is a complex operation in a real optimizer
        # For now, we'll just return the original plan
        return op


class RedundantSubqueryRemoval(OptimizationRule):
    """Remove redundant subqueries"""
    
    def apply(self, plan: LogicalOperator) -> LogicalOperator:
        """Apply redundant subquery removal to the logical plan"""
        # This is a complex operation in a real optimizer
        # For now, we'll just return the original plan
        return plan


class JoinReordering(OptimizationRule):
    """Reorder joins to minimize the size of intermediate results"""
    
    def apply(self, plan: LogicalOperator) -> LogicalOperator:
        """Apply join reordering to the logical plan"""
        # This would require statistics about table sizes
        # For now, we'll just return the original plan 
        return plan


class Optimizer:
    """SQL query optimizer that applies optimization rules to logical plans"""
    
    def __init__(self):
        self.rules = [
            PredicatePushdown(),
            ProjectionPruning(),
            RedundantSubqueryRemoval(),
            JoinReordering()
        ]
    
    def optimize(self, logical_plan: LogicalOperator) -> LogicalOperator:
        """Apply all optimization rules to the logical plan"""
        optimized_plan = logical_plan
        
        # Apply each rule in sequence
        for rule in self.rules:
            optimized_plan = rule.apply(optimized_plan)
        
        return optimized_plan


# Example usage
if __name__ == "__main__":
    from sql_parser import SQLParser
    from logical_plan import ASTToLogicalConverter
    
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
    
    parser = SQLParser(sql)
    ast = parser.parse()
    
    converter = ASTToLogicalConverter()
    logical_plan = converter.convert(ast)
    
    optimizer = Optimizer()
    optimized_plan = optimizer.optimize(logical_plan)
    
    print("Original Logical Plan:")
    print(logical_plan)
    print("\nOptimized Logical Plan:")
    print(optimized_plan)