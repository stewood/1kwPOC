"""
Database Management Package

This package provides database functionality for the 1kw POC project, including:
- SQLite database management
- Trade data storage and retrieval
- Price history tracking
- Performance analysis and reporting

Main Components:
    db_manager: Core database operations manager
    example_usage: Example code demonstrating database usage
"""

from .db_manager import DatabaseManager

__all__ = ['DatabaseManager']
