"""
SQLite database schema for storing Option Samurai trade opportunities and price history.

This module defines the database schema for the 1kw POC project, including:
- Schema version tracking
- Trade management tables
- Indexes for performance optimization
- Triggers for automated timestamp updates

The schema supports both credit spreads and iron condors, with appropriate constraints
and validations to ensure data integrity.

Version: 1.0
"""

SCHEMA_VERSION = 1

# Schema creation statements
CREATE_SCHEMA_VERSION = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_TRADES = """
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_date TIMESTAMP NOT NULL,
    symbol TEXT NOT NULL,
    strategy TEXT NOT NULL CHECK (strategy IN ('CREDIT_SPREAD', 'IRON_CONDOR')),
    expiration_date DATE NOT NULL,
    call_short_strike DECIMAL(10,2) NOT NULL,
    call_long_strike DECIMAL(10,2) NOT NULL,
    put_short_strike DECIMAL(10,2),
    put_long_strike DECIMAL(10,2),
    net_credit DECIMAL(10,2) NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN' 
        CHECK (status IN ('OPEN', 'CLOSED', 'EXPIRED')),
    close_date TIMESTAMP,
    close_price DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_credit_spread CHECK (
        (strategy = 'CREDIT_SPREAD' AND 
         put_short_strike IS NULL AND 
         put_long_strike IS NULL AND
         call_short_strike < call_long_strike) OR
        (strategy = 'IRON_CONDOR' AND 
         put_short_strike IS NOT NULL AND 
         put_long_strike IS NOT NULL AND
         put_long_strike < put_short_strike AND 
         call_short_strike < call_long_strike)
    )
);
"""

# Indexes
CREATE_TRADES_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);",
    "CREATE INDEX IF NOT EXISTS idx_trades_scan_date ON trades(scan_date);",
    "CREATE INDEX IF NOT EXISTS idx_trades_expiration ON trades(expiration_date);",
    "CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);",
    "CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy);"
]

# Triggers for updated_at
CREATE_TRADES_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS update_trades_timestamp 
    AFTER UPDATE ON trades
BEGIN
    UPDATE trades SET updated_at = CURRENT_TIMESTAMP 
    WHERE id = NEW.id;
END;
"""

def get_all_statements():
    """
    Returns all SQL statements needed to create the database schema.
    
    This function aggregates all the SQL statements required to:
    - Create tables
    - Set up indexes
    - Create triggers
    - Initialize schema version
    
    Returns:
        list[str]: A list of SQL statements in the order they should be executed
    """
    statements = [
        CREATE_SCHEMA_VERSION,
        CREATE_TRADES,
        CREATE_TRADES_TRIGGER
    ]
    statements.extend(CREATE_TRADES_INDEXES)
    return statements