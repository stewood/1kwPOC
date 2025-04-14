-- Migration to add support for debit spreads

-- 1. Create new tables with updated constraints
CREATE TABLE IF NOT EXISTS active_trades_new (
    trade_id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    underlying_price DECIMAL(10,2) NOT NULL,
    trade_type TEXT NOT NULL CHECK (trade_type IN ('BULL_PUT', 'BEAR_CALL', 'IRON_CONDOR', 'BULL_CALL', 'BEAR_PUT')),
    entry_date TIMESTAMP NOT NULL,
    expiration_date DATE NOT NULL,
    short_put DECIMAL(10,2),
    long_put DECIMAL(10,2),
    short_put_symbol TEXT,
    long_put_symbol TEXT,
    short_call DECIMAL(10,2),
    long_call DECIMAL(10,2),
    short_call_symbol TEXT,
    long_call_symbol TEXT,
    theoretical_credit DECIMAL(10,2) NOT NULL,
    actual_credit DECIMAL(10,2),
    net_credit DECIMAL(10,2) NOT NULL,
    entry_price_source TEXT NOT NULL CHECK (entry_price_source IN ('optionsamurai', 'tradier')),
    num_contracts INTEGER NOT NULL DEFAULT 1 CHECK (num_contracts > 0),
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'CLOSING', 'EXPIRED')),
    spread_type TEXT NOT NULL DEFAULT 'CREDIT' CHECK (spread_type IN ('CREDIT', 'DEBIT')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS completed_trades_new (
    trade_id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    underlying_entry_price DECIMAL(10,2) NOT NULL,
    underlying_exit_price DECIMAL(10,2) NOT NULL,
    trade_type TEXT NOT NULL,
    entry_date TIMESTAMP NOT NULL,
    expiration_date DATE NOT NULL,
    close_date TIMESTAMP NOT NULL,
    short_put DECIMAL(10,2),
    long_put DECIMAL(10,2),
    short_put_symbol TEXT,
    long_put_symbol TEXT,
    short_call DECIMAL(10,2),
    long_call DECIMAL(10,2),
    short_call_symbol TEXT,
    long_call_symbol TEXT,
    entry_credit DECIMAL(10,2) NOT NULL,
    exit_debit DECIMAL(10,2) CHECK (exit_debit >= 0),
    num_contracts INTEGER NOT NULL CHECK (num_contracts > 0),
    actual_profit_loss DECIMAL(10,2) NOT NULL,
    exit_type TEXT NOT NULL CHECK (exit_type IN ('EXPIRED', 'CLOSED_EARLY', 'STOPPED_OUT', 'ROLLED')),
    spread_type TEXT NOT NULL DEFAULT 'CREDIT' CHECK (spread_type IN ('CREDIT', 'DEBIT')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. Copy data from old tables to new tables
INSERT INTO active_trades_new 
SELECT 
    trade_id, symbol, underlying_price, trade_type, entry_date, expiration_date,
    short_put, long_put, short_put_symbol, long_put_symbol,
    short_call, long_call, short_call_symbol, long_call_symbol,
    theoretical_credit, actual_credit, net_credit, entry_price_source,
    num_contracts, status,
    CASE WHEN net_credit > 0 THEN 'CREDIT' ELSE 'DEBIT' END as spread_type,
    created_at, updated_at
FROM active_trades;

INSERT INTO completed_trades_new 
SELECT 
    trade_id, symbol, underlying_entry_price, underlying_exit_price,
    trade_type, entry_date, expiration_date, close_date,
    short_put, long_put, short_put_symbol, long_put_symbol,
    short_call, long_call, short_call_symbol, long_call_symbol,
    entry_credit, exit_debit, num_contracts, actual_profit_loss,
    exit_type,
    CASE WHEN entry_credit > 0 THEN 'CREDIT' ELSE 'DEBIT' END as spread_type,
    created_at, completed_at
FROM completed_trades;

-- 3. Drop old tables
DROP TABLE active_trades;
DROP TABLE completed_trades;

-- 4. Rename new tables to original names
ALTER TABLE active_trades_new RENAME TO active_trades;
ALTER TABLE completed_trades_new RENAME TO completed_trades;

-- 5. Recreate indexes
CREATE INDEX IF NOT EXISTS idx_active_trades_symbol ON active_trades(symbol);
CREATE INDEX IF NOT EXISTS idx_active_trades_status ON active_trades(status);
CREATE INDEX IF NOT EXISTS idx_active_trades_expiration ON active_trades(expiration_date);
CREATE INDEX IF NOT EXISTS idx_completed_trades_symbol ON completed_trades(symbol);
CREATE INDEX IF NOT EXISTS idx_completed_trades_dates ON completed_trades(entry_date, close_date);

-- 6. Recreate triggers
DROP TRIGGER IF EXISTS update_active_trades_timestamp;
CREATE TRIGGER update_active_trades_timestamp 
    AFTER UPDATE ON active_trades
BEGIN
    UPDATE active_trades SET updated_at = CURRENT_TIMESTAMP 
    WHERE trade_id = NEW.trade_id;
END; 