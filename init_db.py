#!/usr/bin/env python3

from src.database.db_manager import DatabaseManager

def main():
    """Initialize the database with the schema."""
    print("Initializing database...")
    db = DatabaseManager()
    print("Database initialization complete.")

if __name__ == "__main__":
    main() 