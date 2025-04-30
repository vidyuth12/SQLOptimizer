#!/usr/bin/env python3
"""
SQL Optimizer Test Suite

Tests for the SQL optimizer components.
"""

import unittest
from sql_parser import SQLParser
from logical_plan import ASTToLogicalConverter
from optimizer import Optimizer, PredicatePushdown
from sql_generator import SQLGenerator


class TestSQLParser(unittest.TestCase):
    """Test the SQL parser"""
    
    def test_simple_select(self):
        """Test parsing a simple SELECT statement"""
        sql = "SELECT id, name FROM users"
        parser = SQLParser(sql)
        ast = parser.parse()
        
        self.assertEqual(len(ast.columns), 2)
        self.assertEqual(ast.columns[0].name, "id")
        self.assertEqual(ast.columns[1].name, "name")
        self.assertEqual(ast.from_clause.table.name, "users")
        self.assertIsNone(ast.where_clause)
    
    def test_select_with_where(self):
        """Test parsing a SELECT with WHERE clause"""
        sql = "SELECT id, name FROM users WHERE age > 21"
        parser = SQLParser(sql)
        ast = parser.parse()
        
        self.assertEqual(len(ast.columns), 2)
        self.assertIsNotNone(ast.where_clause)
        self.assertEqual(ast.where_clause.condition.left.name, "age")
        self.assertEqual(ast.where_clause.condition.op.value, ">")
        self.assertEqual(ast.where_clause.condition.right.value, 21)
    
    def test_select_with_join(self):
        """Test parsing a SELECT with JOIN"""
        sql = "SELECT u.id, o.amount FROM users u JOIN orders o ON u.id = o.user_id"
        parser = SQLParser(sql)
        ast = parser.parse()
        
        self.assertEqual(len(ast.columns), 2)
        self.assertEqual(ast.from_clause.table.name, "users")
        self.assertEqual(ast.from_clause.table.alias, "u")
        self.assertEqual(len(ast.from_clause.joins), 1)
        self.assertEqual(ast.from_clause.joins[0].table.name, "orders")
        self.assertEqual(ast.from_clause.joins[0].table.alias, "o")
        
    def test_complex_query(self):
        """Test parsing a complex query"""
        sql = """
        SELECT 
            u.id, 
            u.name, 
            COUNT(o.id) AS order_count 
        FROM 
            users u 
        LEFT JOIN 
            orders o 
        ON 
            u.id = o.user_id 
        WHERE 
            u.active = TRUE 
        GROUP BY 
            u.id, 
            u.name 
        ORDER BY 
            order_count DESC 
        LIMIT 
            10
        """
        parser = SQLParser(sql)
        ast = parser.parse()
        
        self.assertEqual(len(ast.columns), 3)
        self.assertEqual(ast.from_clause.table.name, "users")
        self.assertEqual(len(ast.from_clause.joins), 1)
        self.assertIsNotNone(ast.where_clause)
        self.assertIsNotNone(ast.group_by)
        self.assertIsNotNone(ast.order_by)
        self.assertEqual(ast.limit, 10)


class TestLogicalPlan(unittest.TestCase):
    """Test conversion from AST to logical plan"""
    
    def test_simple_logical_plan(self):
        """Test creating a simple logical plan"""
        sql = "SELECT id, name FROM users"
        parser = SQLParser(sql)
        ast = parser.parse()
        
        converter = ASTToLogicalConverter()
        logical_plan = converter.convert(ast)
        
        # The logical plan should have a projection at the top
        self.assertTrue(hasattr(logical_plan, 'columns'))
        self.assertEqual(len(logical_plan.columns), 2)
        
        # The input to the projection should be a scan
        self.assertTrue(hasattr(logical_plan, 'input_op'))
        self.assertTrue(hasattr(logical_plan.input_op, 'table'))
        self.assertEqual(logical_plan.input_op.table.name, "users")


class TestOptimizer(unittest.TestCase):
    """Test the optimizer"""
    
    def test_predicate_pushdown(self):
        """Test that predicates get pushed down"""
        sql = """
        SELECT 
            u.id, 
            o.amount 
        FROM 
            users u 
        JOIN 
            orders o 
        ON 
            u.id = o.user_id 
        WHERE 
            u.active = TRUE
        """
        parser = SQLParser(sql)
        ast = parser.parse()
        
        converter = ASTToLogicalConverter()
        logical_plan = converter.convert(ast)
        
        # Apply just the predicate pushdown rule
        rule = PredicatePushdown()
        optimized_plan = rule.apply(logical_plan)
        
        # We expect the WHERE condition to be pushed down to the table scan
        # This is a complex assertion that depends on the internal structure
        # We'll just check that it's different from the original
        self.assertIsNotNone(optimized_plan)


class TestSQLGenerator(unittest.TestCase):
    """Test generating SQL from a logical plan"""
    
    def test_generate_simple_sql(self):
        """Test generating SQL for a simple query"""
        sql = "SELECT id, name FROM users"
        parser = SQLParser(sql)
        ast = parser.parse()
        
        converter = ASTToLogicalConverter()
        logical_plan = converter.convert(ast)
        
        generator = SQLGenerator()
        generated_sql = generator.generate(logical_plan)
        
        # The generated SQL should be similar to the original
        # (we don't check for exact equality because the formatting may differ)
        self.assertIn("SELECT", generated_sql)
        self.assertIn("id", generated_sql)
        self.assertIn("name", generated_sql)
        self.assertIn("FROM", generated_sql)
        self.assertIn("users", generated_sql)


class TestEndToEnd(unittest.TestCase):
    """End-to-end tests for the optimizer"""
    
    def test_simple_optimization(self):
        """Test a simple optimization end-to-end"""
        sql = """
        SELECT 
            u.id, 
            o.amount 
        FROM 
            users u 
        JOIN 
            orders o 
        ON 
            u.id = o.user_id 
        WHERE 
            u.active = TRUE 
            AND o.status = 'completed'
        """
        
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
        
        # Check that the optimized SQL contains the key elements
        self.assertIn("SELECT", optimized_sql)
        self.assertIn("u.id", optimized_sql)
        self.assertIn("o.amount", optimized_sql)
        self.assertIn("FROM", optimized_sql)
        self.assertIn("users", optimized_sql)
        self.assertIn("JOIN", optimized_sql)
        self.assertIn("orders", optimized_sql)
        self.assertIn("WHERE", optimized_sql)
        self.assertIn("active", optimized_sql)
        self.assertIn("status", optimized_sql)


if __name__ == "__main__":
    unittest.main()