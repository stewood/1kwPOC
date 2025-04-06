"""
SQLite database schema for storing Option Samurai trade opportunities and price history.
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

CREATE_PRICE_CHECKS = """
CREATE TABLE IF NOT EXISTS price_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id INTEGER NOT NULL,
    check_date TIMESTAMP NOT NULL,
    underlying_price DECIMAL(10,2) NOT NULL,
    current_value DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(trade_id) REFERENCES trades(id),
    UNIQUE(trade_id, check_date)
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

CREATE_PRICE_CHECKS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_price_checks_trade_date ON price_checks(trade_id, check_date);"
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
    """Returns all SQL statements needed to create the schema."""
    statements = [
        CREATE_SCHEMA_VERSION,
        CREATE_TRADES,
        CREATE_PRICE_CHECKS,
        CREATE_TRADES_TRIGGER
    ]
    statements.extend(CREATE_TRADES_INDEXES)
    statements.extend(CREATE_PRICE_CHECKS_INDEXES)
    return statements