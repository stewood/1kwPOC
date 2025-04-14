# Database Schema Documentation

## Overview
This document details the database schema for storing option trades, including active trades, completed trades, and their associated audit trails.

## Core Tables

### active_trades
Stores all currently open or active option trades.

```sql
CREATE TABLE active_trades (
    trade_id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,                    -- Underlying symbol (e.g., 'SPY')
    underlying_price DECIMAL(10,2) NOT NULL, -- Price of underlying at entry
    trade_type TEXT NOT NULL CHECK (trade_type IN ('BULL_PUT', 'BEAR_CALL', 'IRON_CONDOR', 'BULL_CALL', 'BEAR_PUT')),
    entry_date TIMESTAMP NOT NULL,
    expiration_date DATE NOT NULL,
    
    -- Put leg details
    short_put DECIMAL(10,2),
    long_put DECIMAL(10,2),
    short_put_symbol TEXT,    -- OCC Option Symbol
    long_put_symbol TEXT,     -- OCC Option Symbol
    
    -- Call leg details
    short_call DECIMAL(10,2),
    long_call DECIMAL(10,2),
    short_call_symbol TEXT,   -- OCC Option Symbol
    long_call_symbol TEXT,    -- OCC Option Symbol
    
    net_credit DECIMAL(10,2) NOT NULL,  -- Can be negative for debit spreads
    num_contracts INTEGER NOT NULL DEFAULT 1 CHECK (num_contracts > 0),
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'CLOSING', 'EXPIRED')),
    spread_type TEXT NOT NULL DEFAULT 'CREDIT' CHECK (spread_type IN ('CREDIT', 'DEBIT')),
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### completed_trades
Stores historical trades that have been closed or expired.

```sql
CREATE TABLE completed_trades (
    trade_id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    underlying_entry_price DECIMAL(10,2) NOT NULL,
    underlying_exit_price DECIMAL(10,2) NOT NULL,
    trade_type TEXT NOT NULL CHECK (trade_type IN ('BULL_PUT', 'BEAR_CALL', 'IRON_CONDOR', 'BULL_CALL', 'BEAR_PUT')),
    entry_date TIMESTAMP NOT NULL,
    expiration_date DATE NOT NULL,
    close_date TIMESTAMP NOT NULL,
    
    -- Put leg details
    short_put DECIMAL(10,2),
    long_put DECIMAL(10,2),
    short_put_symbol TEXT,
    long_put_symbol TEXT,
    
    -- Call leg details
    short_call DECIMAL(10,2),
    long_call DECIMAL(10,2),
    short_call_symbol TEXT,
    long_call_symbol TEXT,
    
    entry_credit DECIMAL(10,2) NOT NULL,  -- Can be negative for debit spreads
    exit_debit DECIMAL(10,2) CHECK (exit_debit >= 0),
    num_contracts INTEGER NOT NULL CHECK (num_contracts > 0),
    actual_profit_loss DECIMAL(10,2) NOT NULL,
    exit_type TEXT NOT NULL CHECK (exit_type IN ('EXPIRED', 'CLOSED_EARLY', 'STOPPED_OUT', 'ROLLED')),
    spread_type TEXT NOT NULL DEFAULT 'CREDIT' CHECK (spread_type IN ('CREDIT', 'DEBIT')),
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### trade_status_history
Tracks all status changes for audit purposes.

```sql
CREATE TABLE trade_status_history (
    history_id INTEGER PRIMARY KEY,
    trade_id INTEGER NOT NULL,
    old_status TEXT NOT NULL,
    new_status TEXT NOT NULL,
    change_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(trade_id) REFERENCES active_trades(trade_id)
);
```

## Constraints

### active_trades Constraints
1. Valid trade type checking (now includes BULL_CALL and BEAR_PUT)
2. Date validation (expiration > entry)
3. Trade structure validation:
   - Bull Put: requires put strikes only
   - Bear Call: requires call strikes only
   - Iron Condor: requires all strikes with proper relationships
   - Bull Call: requires call strikes only
   - Bear Put: requires put strikes only
4. Spread type validation (CREDIT or DEBIT)

### completed_trades Constraints
1. Date validations (close <= expiration, close >= entry)
2. Valid exit types
3. Spread type validation (CREDIT or DEBIT)

## Indexes
```sql
CREATE INDEX idx_active_trades_symbol ON active_trades(symbol);
CREATE INDEX idx_active_trades_status ON active_trades(status);
CREATE INDEX idx_active_trades_expiration ON active_trades(expiration_date);
CREATE INDEX idx_completed_trades_symbol ON completed_trades(symbol);
CREATE INDEX idx_completed_trades_dates ON completed_trades(entry_date, close_date);
```

## Triggers

### Updated Timestamp
```sql
CREATE TRIGGER update_active_trades_timestamp 
    AFTER UPDATE ON active_trades
BEGIN
    UPDATE active_trades SET updated_at = CURRENT_TIMESTAMP 
    WHERE trade_id = NEW.trade_id;
END;
```

### Status Change Logging
```sql
CREATE TRIGGER log_status_change
    AFTER UPDATE OF status ON active_trades
    WHEN NEW.status != OLD.status
BEGIN
    INSERT INTO trade_status_history (trade_id, old_status, new_status)
    VALUES (OLD.trade_id, OLD.status, NEW.status);
END;
```

## Extension Points
The schema is designed to be extensible through additional related tables:
1. Trade analytics (using trade_id)
2. Price history tracking
3. Market conditions
4. Performance metrics
5. Report tracking

## Option Symbols
Option symbols follow the OCC format:
- Example: SPY240419P410000
  * SPY: Underlying symbol
  * 240419: Expiration (YYMMDD)
  * P/C: Put/Call
  * 410000: Strike price ($410.00)

## Trade Types
The system now supports both credit and debit spreads:

### Credit Spreads
- BULL_PUT: Bullish put credit spread
- BEAR_CALL: Bearish call credit spread
- IRON_CONDOR: Iron condor (combination of put and call credit spreads)

### Debit Spreads
- BULL_CALL: Bullish call debit spread
- BEAR_PUT: Bearish put debit spread

## Spread Types
Each trade is marked with a spread_type:
- CREDIT: Trade that receives a credit at entry
- DEBIT: Trade that requires a debit at entry 