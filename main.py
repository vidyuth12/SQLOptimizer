#!/usr/bin/env python3
"""
SQL Optimizer CLI

A command-line interface for the SQL optimizer.
"""

import argparse
import sys
import traceback
from sql_parser import SQLParser
from logical_plan import ASTToLogicalConverter
from optimizer import Optimizer
from sql_generator import SQLGenerator


def optimize_sql(sql: str, verbose: bool = False) -> str:
    """
    Optimize a SQL query.
    
    Args:
        sql: The SQL query to optimize
        verbose: Whether to print intermediate steps
        
    Returns:
        The optimized SQL query
    """
    try:
        # Parse the SQL into an AST
        parser = SQLParser(sql)
        ast = parser.parse()
        
        if verbose:
            print("\nAST:")
            print(ast)
        
        # Convert the AST to a logical plan
        converter = ASTToLogicalConverter()
        logical_plan = converter.convert(ast)
        
        if verbose:
            print("\nLogical Plan:")
            print(logical_plan)
        
        # Optimize the logical plan
        optimizer = Optimizer()
        optimized_plan = optimizer.optimize(logical_plan)
        
        if verbose:
            print("\nOptimized Logical Plan:")
            print(optimized_plan)
        
        # Generate optimized SQL
        generator = SQLGenerator()
        optimized_sql = generator.generate(optimized_plan)
        
        return optimized_sql
        
    except Exception as e:
        if verbose:
            traceback.print_exc()
        return f"Error optimizing SQL: {str(e)}"


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="SQL Query Optimizer")
    parser.add_argument(
        "sql",
        nargs="?",
        help="SQL query to optimize. If not provided, read from stdin."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show intermediate steps"
    )
    parser.add_argument(
        "-f", "--file",
        type=str,
        help="Read SQL from file"
    )
    
    args = parser.parse_args()
    
    # Get the SQL query from arguments, file, or stdin
    sql = ""
    if args.sql:
        sql = args.sql
    elif args.file:
        try:
            with open(args.file, "r") as f:
                sql = f.read()
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("Reading SQL from stdin (press Ctrl+D when done):")
        sql = sys.stdin.read()
    
    if not sql.strip():
        print("Error: No SQL query provided", file=sys.stderr)
        sys.exit(1)
    
    # Optimize the SQL
    optimized_sql = optimize_sql(sql, args.verbose)
    
    # Print the result
    if args.verbose:
        print("\nOptimized SQL:")
    print(optimized_sql)


if __name__ == "__main__":
    main()