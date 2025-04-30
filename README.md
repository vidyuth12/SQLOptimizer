# SQL Optimizer

A lightweight SQL optimizer built in Python that parses SQL queries into an Abstract Syntax Tree (AST), converts them to a logical plan, applies basic query optimizations, and generates optimized SQL. Inspired by [SQLGlot](https://github.com/tobymao/sqlglot), this project is modular, educational, and extensible.


## ✨ Features

-  Custom SQL parser (recursive descent) for `SELECT` queries
-  Abstract Syntax Tree (AST) representation of SQL
-  Logical plan generation from AST
-  Basic optimization rules (e.g., predicate pushdown, projection pruning)
-  SQL code generation from optimized logical plan
-  CLI interface to parse and optimize SQL from file or stdin


## Supported SQL Constructs

  - Supported SQL Constructs
  - SELECT, FROM, WHERE, JOIN (INNER, LEFT, RIGHT, FULL)
  - GROUP BY, ORDER BY, LIMIT
  - Table/column aliases
  - Binary expressions (=, !=, <, >, <=, >=)
  - Boolean logic (AND, OR)

## Requirements
      - Python 3.7+

## Future Enhancements
    
  - Cost-based optimization
  - Subquery flattening
  - Transpile between SQL dialects
  - Expression simplification (constant folding)

