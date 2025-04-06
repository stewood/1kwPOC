"""
Database initialization script.
Creates SQLite database with proper schema.
"""

import sqlite3
from pathlib import Path
from .schema import get_all_statements, SCHEMA_VERSION

def init_db(db_path: str = 'trades.db') -> None:
    """
    Initialize the database with proper schema.
    
    Args:
        db_path: Path to the SQLite database file
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