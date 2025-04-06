"""
Database initialization script for the 1kw POC project.

This module handles the initial setup of the SQLite database, including:
- Creating the database file if it doesn't exist
- Setting up the schema using statements from schema.py
- Enabling SQLite features like foreign key support
- Setting the schema version

Usage:
    python -m db.init_db [db_path]
"""

import sqlite3
from pathlib import Path
from .schema import get_all_statements, SCHEMA_VERSION

def init_db(db_path: str = 'trades.db') -> None:
    """
    Initialize the SQLite database with the proper schema.
    
    This function:
    1. Creates the database file and parent directories if they don't exist
    2. Enables SQLite foreign key support
    3. Creates all required tables, indexes, and triggers
    4. Sets the schema version
    
    Args:
        db_path (str): Path to the SQLite database file. Defaults to 'trades.db'
        
    Raises:
        sqlite3.Error: If there's an error during database initialization
    """
    db_path = Path(db_path)
    
    # Create directory if it doesn't exist
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    with sqlite3.connect(db_path) as conn:
        # Enable foreign key support
        conn.execute("PRAGMA foreign_keys = ON;")
        
        # Create schema
        for statement in get_all_statements():
            conn.execute(statement)
            
        # Set schema version
        conn.execute("INSERT OR REPLACE INTO schema_version (version) VALUES (?);",
                    (SCHEMA_VERSION,))
        
        conn.commit()

if __name__ == '__main__':
    init_db() 