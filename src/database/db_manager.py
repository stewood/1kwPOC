"""
Database manager for Option Samurai trade tracking.
Handles all database operations for storing and retrieving trade information.
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import logging
from contextlib import contextmanager
from typing import Dict, List, Optional, Union, Any, Tuple
from threading import Lock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/database.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages all database operations for the trading system."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the database manager.
        
        Args:
            db_path: Optional path to the database file. If None, uses default path.
        """
        # Keep track of open connections
        self._connections = []
        self._connections_lock = Lock()
        
        # Ensure data directory exists
        self.data_dir = Path('data/db')
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Set database path
        self.db_path = Path(db_path) if db_path else self.data_dir / 'trades.db'
        
        # Initialize database
        self.initialize_database()
    
    def close(self):
        """Close all open database connections."""
        with self._connections_lock:
            for conn in self._connections:
                try:
                    conn.close()
                except Exception as e:
                    logger.error(f"Error closing connection: {e}")
            self._connections.clear()
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.
        Ensures connections are properly closed after use.
        Thread-safe: each thread gets its own connection.
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Allows dictionary access to rows
            with self._connections_lock:
                self._connections.append(conn)  # Track this connection
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                try:
                    conn.close()
                    with self._connections_lock:
                        if conn in self._connections:
                            self._connections.remove(conn)  # Remove from tracked connections
                except Exception as e:
                    logger.error(f"Error closing connection: {e}")
    
    def initialize_database(self):
        """Create database tables if they don't exist."""
        try:
            with self.get_connection() as conn:
                # Create active_trades table
                conn.execute('''
                CREATE TABLE IF NOT EXISTS active_trades (
                    trade_id INTEGER PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    underlying_price DECIMAL(10,2) NOT NULL,
                    trade_type TEXT NOT NULL CHECK (trade_type IN ('BULL_PUT', 'BEAR_CALL', 'IRON_CONDOR')),
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
                    net_credit DECIMAL(10,2) NOT NULL CHECK (net_credit > 0),
                    num_contracts INTEGER NOT NULL DEFAULT 1 CHECK (num_contracts > 0),
                    status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'CLOSING', 'EXPIRED')),
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                
                # Create completed_trades table
                conn.execute('''
                CREATE TABLE IF NOT EXISTS completed_trades (
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
                    entry_credit DECIMAL(10,2) NOT NULL CHECK (entry_credit > 0),
                    exit_debit DECIMAL(10,2) CHECK (exit_debit >= 0),
                    num_contracts INTEGER NOT NULL CHECK (num_contracts > 0),
                    actual_profit_loss DECIMAL(10,2) NOT NULL,
                    exit_type TEXT NOT NULL CHECK (exit_type IN ('EXPIRED', 'CLOSED_EARLY', 'STOPPED_OUT', 'ROLLED')),
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                
                # Create trade_status_history table
                conn.execute('''
                CREATE TABLE IF NOT EXISTS trade_status_history (
                    history_id INTEGER PRIMARY KEY,
                    trade_id INTEGER NOT NULL,
                    old_status TEXT NOT NULL,
                    new_status TEXT NOT NULL,
                    change_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(trade_id) REFERENCES active_trades(trade_id)
                )
                ''')
                
                # Create option_price_tracking table
                conn.execute('''
                CREATE TABLE IF NOT EXISTS option_price_tracking (
                    tracking_id INTEGER PRIMARY KEY,
                    trade_id INTEGER NOT NULL,
                    tracking_date DATE NOT NULL,
                    option_symbol TEXT NOT NULL,
                    bid DECIMAL(10,2),
                    ask DECIMAL(10,2),
                    last DECIMAL(10,2),
                    mark DECIMAL(10,2),
                    bid_size INTEGER,
                    ask_size INTEGER,
                    volume INTEGER,
                    open_interest INTEGER,
                    exchange TEXT,
                    greeks_update_time TIMESTAMP,
                    delta DECIMAL(10,4),
                    gamma DECIMAL(10,4),
                    theta DECIMAL(10,4),
                    vega DECIMAL(10,4),
                    rho DECIMAL(10,4),
                    phi DECIMAL(10,4),
                    bid_iv DECIMAL(10,4),
                    mid_iv DECIMAL(10,4),
                    ask_iv DECIMAL(10,4),
                    smv_vol DECIMAL(10,4),
                    contract_size INTEGER,
                    expiration_type TEXT,
                    is_closing_only BOOLEAN,
                    is_tradeable BOOLEAN,
                    is_market_closed BOOLEAN,
                    is_complete BOOLEAN DEFAULT FALSE,
                    last_update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                
                # Create indexes
                conn.execute('CREATE INDEX IF NOT EXISTS idx_active_trades_symbol ON active_trades(symbol)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_active_trades_status ON active_trades(status)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_active_trades_expiration ON active_trades(expiration_date)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_completed_trades_symbol ON completed_trades(symbol)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_completed_trades_dates ON completed_trades(entry_date, close_date)')
                
                # Create trigger for updated_at
                conn.execute('''
                CREATE TRIGGER IF NOT EXISTS update_active_trades_timestamp 
                    AFTER UPDATE ON active_trades
                BEGIN
                    UPDATE active_trades SET updated_at = CURRENT_TIMESTAMP 
                    WHERE trade_id = NEW.trade_id;
                END;
                ''')
                
                # Create trigger for status change logging
                conn.execute('''
                CREATE TRIGGER IF NOT EXISTS log_status_change
                    AFTER UPDATE OF status ON active_trades
                    WHEN NEW.status != OLD.status
                BEGIN
                    INSERT INTO trade_status_history (trade_id, old_status, new_status)
                    VALUES (OLD.trade_id, OLD.status, NEW.status);
                END;
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except sqlite3.Error as e:
            logger.error(f"Error initializing database: {e}")
            raise 

    def save_new_trade(self, trade_data: Dict[str, Any]) -> int:
        """
        Save a new trade from Option Samurai scan results.
        
        Args:
            trade_data: Dictionary containing trade information
                Required keys:
                - symbol: Stock symbol
                - underlying_price: Current stock price
                - trade_type: BULL_PUT, BEAR_CALL, or IRON_CONDOR
                - expiration_date: Option expiration date
                - net_credit: Credit received for the trade
                - num_contracts: Number of contracts
                Optional keys (depending on trade_type):
                - short_put, long_put: Strike prices for put options
                - short_call, long_call: Strike prices for call options
                - short_put_symbol, long_put_symbol: OCC option symbols
                - short_call_symbol, long_call_symbol: OCC option symbols
        
        Returns:
            trade_id: ID of the newly created trade
        """
        required_fields = {'symbol', 'underlying_price', 'trade_type', 
                         'expiration_date', 'net_credit', 'num_contracts'}
        
        if missing := required_fields - set(trade_data.keys()):
            raise ValueError(f"Missing required fields: {missing}")
            
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                INSERT INTO active_trades (
                    symbol, underlying_price, trade_type, entry_date,
                    expiration_date, short_put, long_put, short_put_symbol,
                    long_put_symbol, short_call, long_call, short_call_symbol,
                    long_call_symbol, net_credit, num_contracts
                ) VALUES (
                    :symbol, :underlying_price, :trade_type, CURRENT_TIMESTAMP,
                    :expiration_date, :short_put, :long_put, :short_put_symbol,
                    :long_put_symbol, :short_call, :long_call, :short_call_symbol,
                    :long_call_symbol, :net_credit, :num_contracts
                )
                ''', trade_data)
                
                trade_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Saved new trade {trade_id} for {trade_data['symbol']}")
                return trade_id
                
        except sqlite3.Error as e:
            logger.error(f"Error saving trade: {e}")
            raise
    
    def update_trade_status(self, trade_id: int, new_status: str) -> None:
        """
        Update the status of an active trade.
        
        Args:
            trade_id: ID of the trade to update
            new_status: New status (OPEN, CLOSING, or EXPIRED)
        """
        valid_statuses = {'OPEN', 'CLOSING', 'EXPIRED'}
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        
        try:
            with self.get_connection() as conn:
                conn.execute('''
                UPDATE active_trades 
                SET status = ?
                WHERE trade_id = ?
                ''', (new_status, trade_id))
                
                conn.commit()
                logger.info(f"Updated trade {trade_id} status to {new_status}")
                
        except sqlite3.Error as e:
            logger.error(f"Error updating trade status: {e}")
            raise
    
    def complete_trade(self, trade_id: int, exit_data: Dict[str, Any]) -> None:
        """
        Move a trade from active to completed status.
        
        Args:
            trade_id: ID of the trade to complete
            exit_data: Dictionary containing exit information
                Required keys:
                - underlying_exit_price: Stock price at exit
                - exit_debit: Cost to close position (0 if expired)
                - actual_profit_loss: Actual P&L for the trade
                - exit_type: EXPIRED, CLOSED_EARLY, STOPPED_OUT, or ROLLED
        """
        required_fields = {'underlying_exit_price', 'exit_debit', 
                         'actual_profit_loss', 'exit_type'}
        
        if missing := required_fields - set(exit_data.keys()):
            raise ValueError(f"Missing required exit fields: {missing}")
        
        try:
            with self.get_connection() as conn:
                # Get the active trade
                cursor = conn.execute('''
                SELECT * FROM active_trades WHERE trade_id = ?
                ''', (trade_id,))
                trade = cursor.fetchone()
                
                if not trade:
                    raise ValueError(f"No active trade found with ID {trade_id}")
                
                # Insert into completed_trades
                conn.execute('''
                INSERT INTO completed_trades (
                    trade_id, symbol, underlying_entry_price, underlying_exit_price,
                    trade_type, entry_date, expiration_date, close_date,
                    short_put, long_put, short_put_symbol, long_put_symbol,
                    short_call, long_call, short_call_symbol, long_call_symbol,
                    entry_credit, exit_debit, num_contracts, actual_profit_loss,
                    exit_type
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?
                )
                ''', (
                    trade['trade_id'], trade['symbol'], trade['underlying_price'],
                    exit_data['underlying_exit_price'], trade['trade_type'],
                    trade['entry_date'], trade['expiration_date'],
                    trade['short_put'], trade['long_put'],
                    trade['short_put_symbol'], trade['long_put_symbol'],
                    trade['short_call'], trade['long_call'],
                    trade['short_call_symbol'], trade['long_call_symbol'],
                    trade['net_credit'], exit_data['exit_debit'],
                    trade['num_contracts'], exit_data['actual_profit_loss'],
                    exit_data['exit_type']
                ))
                
                # Delete from active_trades
                conn.execute('''
                DELETE FROM active_trades WHERE trade_id = ?
                ''', (trade_id,))
                
                conn.commit()
                logger.info(f"Completed trade {trade_id} with exit type {exit_data['exit_type']}")
                
        except sqlite3.Error as e:
            logger.error(f"Error completing trade: {e}")
            raise
    
    def get_active_trades(self, status: Optional[str] = None) -> List[Dict]:
        """
        Get all active trades, optionally filtered by status.
        
        Args:
            status: Optional status filter (OPEN, CLOSING, or EXPIRED)
        
        Returns:
            List of active trades as dictionaries
        """
        try:
            with self.get_connection() as conn:
                if status:
                    cursor = conn.execute('''
                    SELECT * FROM active_trades WHERE status = ?
                    ORDER BY expiration_date ASC
                    ''', (status,))
                else:
                    cursor = conn.execute('''
                    SELECT * FROM active_trades
                    ORDER BY expiration_date ASC
                    ''')
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Error retrieving active trades: {e}")
            raise
    
    def get_trades_by_expiration(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Get active trades expiring within a date range.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        
        Returns:
            List of trades expiring in the date range
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                SELECT * FROM active_trades
                WHERE expiration_date BETWEEN ? AND ?
                ORDER BY expiration_date ASC
                ''', (start_date, end_date))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Error retrieving trades by expiration: {e}")
            raise
    
    def get_trade_history(self, symbol: Optional[str] = None, 
                         limit: int = 100) -> List[Dict]:
        """
        Get completed trade history, optionally filtered by symbol.
        
        Args:
            symbol: Optional symbol to filter by
            limit: Maximum number of trades to return
        
        Returns:
            List of completed trades as dictionaries
        """
        try:
            with self.get_connection() as conn:
                if symbol:
                    cursor = conn.execute('''
                    SELECT * FROM completed_trades
                    WHERE symbol = ?
                    ORDER BY close_date DESC
                    LIMIT ?
                    ''', (symbol, limit))
                else:
                    cursor = conn.execute('''
                    SELECT * FROM completed_trades
                    ORDER BY close_date DESC
                    LIMIT ?
                    ''', (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Error retrieving trade history: {e}")
            raise
    
    def get_trades_expiring_soon(self, days: int = 7) -> List[Dict]:
        """
        Get active trades expiring within the next N days.
        
        Args:
            days: Number of days to look ahead
        
        Returns:
            List of trades expiring soon
        """
        try:
            today = datetime.now().date()
            future = (today + timedelta(days=days)).isoformat()
            
            with self.get_connection() as conn:
                cursor = conn.execute('''
                SELECT * FROM active_trades
                WHERE expiration_date <= ?
                AND status != 'EXPIRED'
                ORDER BY expiration_date ASC
                ''', (future,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Error retrieving expiring trades: {e}")
            raise
    
    def get_trade_performance_stats(self, symbol: Optional[str] = None) -> Dict:
        """
        Get performance statistics for completed trades.
        
        Args:
            symbol: Optional symbol to filter by
        
        Returns:
            Dictionary containing:
            - total_trades: Total number of trades
            - winning_trades: Number of profitable trades
            - total_profit_loss: Total P&L
            - win_rate: Percentage of winning trades
            - average_profit_loss: Average P&L per trade
            - best_trade: Highest profit trade
            - worst_trade: Biggest loss trade
        """
        try:
            with self.get_connection() as conn:
                where_clause = "WHERE symbol = ?" if symbol else ""
                params = (symbol,) if symbol else ()
                
                cursor = conn.execute(f'''
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN actual_profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(actual_profit_loss) as total_profit_loss,
                    AVG(actual_profit_loss) as average_profit_loss,
                    MAX(actual_profit_loss) as best_trade,
                    MIN(actual_profit_loss) as worst_trade
                FROM completed_trades
                {where_clause}
                ''', params)
                
                stats = dict(cursor.fetchone())
                
                # Calculate win rate
                if stats['total_trades'] > 0:
                    stats['win_rate'] = (stats['winning_trades'] / stats['total_trades']) * 100
                else:
                    stats['win_rate'] = 0.0
                
                return stats
                
        except sqlite3.Error as e:
            logger.error(f"Error calculating trade performance: {e}")
            raise
    
    def get_profit_loss_summary(self, 
                              start_date: Optional[str] = None,
                              end_date: Optional[str] = None) -> Dict:
        """
        Get profit/loss summary for a date range.
        
        Args:
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
        
        Returns:
            Dictionary containing:
            - period_profit_loss: Total P&L for period
            - trade_count: Number of trades closed in period
            - average_trade_profit: Average P&L per trade
            - profit_by_type: P&L broken down by trade type
        """
        try:
            with self.get_connection() as conn:
                where_clauses = []
                params = []
                
                if start_date:
                    where_clauses.append("close_date >= ?")
                    params.append(start_date)
                if end_date:
                    where_clauses.append("close_date <= ?")
                    params.append(end_date)
                
                where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
                
                # Get overall summary
                cursor = conn.execute(f'''
                SELECT 
                    SUM(actual_profit_loss) as period_profit_loss,
                    COUNT(*) as trade_count,
                    AVG(actual_profit_loss) as average_trade_profit
                FROM completed_trades
                {where_sql}
                ''', params)
                
                summary = dict(cursor.fetchone())
                
                # Get breakdown by trade type
                cursor = conn.execute(f'''
                SELECT 
                    trade_type,
                    COUNT(*) as count,
                    SUM(actual_profit_loss) as profit_loss,
                    AVG(actual_profit_loss) as avg_profit_loss
                FROM completed_trades
                {where_sql}
                GROUP BY trade_type
                ''', params)
                
                summary['profit_by_type'] = {
                    row['trade_type']: {
                        'count': row['count'],
                        'profit_loss': row['profit_loss'],
                        'avg_profit_loss': row['avg_profit_loss']
                    }
                    for row in cursor
                }
                
                return summary
                
        except sqlite3.Error as e:
            logger.error(f"Error generating P&L summary: {e}")
            raise
    
    def get_trade_status_history(self, trade_id: int) -> List[Dict]:
        """
        Get the status change history for a trade.
        
        Args:
            trade_id: ID of the trade
        
        Returns:
            List of status changes with timestamps
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                SELECT * FROM trade_status_history
                WHERE trade_id = ?
                ORDER BY change_date ASC
                ''', (trade_id,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Error retrieving trade status history: {e}")
            raise

    def create_option_price_tracking(self, trade_id: int, option_data: Dict[str, Any]) -> int:
        """
        Create a new option price tracking record for a trade.
        
        Args:
            trade_id: ID of the trade to track
            option_data: Dictionary containing option data from Tradier API
                Required keys:
                - option_symbol: OCC option symbol
                - tracking_date: Date for this tracking record
                Optional keys (all other fields from Tradier API)
        
        Returns:
            tracking_id: ID of the newly created tracking record
        """
        required_fields = {'option_symbol', 'tracking_date'}
        
        if missing := required_fields - set(option_data.keys()):
            raise ValueError(f"Missing required fields: {missing}")
            
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                INSERT INTO option_price_tracking (
                    trade_id, tracking_date, option_symbol,
                    bid, ask, last, mark,
                    bid_size, ask_size, volume, open_interest,
                    exchange, greeks_update_time,
                    delta, gamma, theta, vega, rho, phi,
                    bid_iv, mid_iv, ask_iv, smv_vol,
                    contract_size, expiration_type,
                    is_closing_only, is_tradeable, is_market_closed
                ) VALUES (
                    :trade_id, :tracking_date, :option_symbol,
                    :bid, :ask, :last, :mark,
                    :bid_size, :ask_size, :volume, :open_interest,
                    :exchange, :greeks_update_time,
                    :delta, :gamma, :theta, :vega, :rho, :phi,
                    :bid_iv, :mid_iv, :ask_iv, :smv_vol,
                    :contract_size, :expiration_type,
                    :is_closing_only, :is_tradeable, :is_market_closed
                )
                ''', {**option_data, 'trade_id': trade_id})
                
                tracking_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Created price tracking record {tracking_id} for trade {trade_id}")
                return tracking_id
                
        except sqlite3.Error as e:
            logger.error(f"Error creating price tracking record: {e}")
            raise

    def update_option_price(self, tracking_id: int, price_data: Dict[str, Any]) -> None:
        """
        Update an existing option price tracking record with new data.
        
        Args:
            tracking_id: ID of the tracking record to update
            price_data: Dictionary containing updated option data
                Any fields from the option_price_tracking table can be updated
        """
        if not price_data:
            raise ValueError("No price data provided for update")
            
        try:
            # Build the update query dynamically based on provided fields
            fields = list(price_data.keys())
            update_fields = [f"{field} = :{field}" for field in fields]
            update_query = f'''
            UPDATE option_price_tracking 
            SET {", ".join(update_fields)}
            WHERE tracking_id = :tracking_id
            '''
            
            with self.get_connection() as conn:
                conn.execute(update_query, {**price_data, 'tracking_id': tracking_id})
                conn.commit()
                logger.info(f"Updated price tracking record {tracking_id}")
                
        except sqlite3.Error as e:
            logger.error(f"Error updating price tracking record: {e}")
            raise

    def get_option_price_history(self, trade_id: int, start_date: Optional[str] = None,
                               end_date: Optional[str] = None) -> List[Dict]:
        """
        Get price history for options in a trade.
        
        Args:
            trade_id: ID of the trade
            start_date: Optional start date in YYYY-MM-DD format
            end_date: Optional end date in YYYY-MM-DD format
        
        Returns:
            List of price tracking records
        """
        try:
            with self.get_connection() as conn:
                query = '''
                SELECT * FROM option_price_tracking
                WHERE trade_id = ?
                '''
                params = [trade_id]
                
                if start_date:
                    query += ' AND tracking_date >= ?'
                    params.append(start_date)
                if end_date:
                    query += ' AND tracking_date <= ?'
                    params.append(end_date)
                    
                query += ' ORDER BY tracking_date ASC, last_update_time ASC'
                
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Error retrieving option price history: {e}")
            raise

    def mark_tracking_complete(self, tracking_id: int) -> None:
        """
        Mark a price tracking record as complete (e.g., at market close).
        
        Args:
            tracking_id: ID of the tracking record to mark complete
        """
        try:
            with self.get_connection() as conn:
                conn.execute('''
                UPDATE option_price_tracking
                SET is_complete = TRUE,
                    is_market_closed = TRUE
                WHERE tracking_id = ?
                ''', (tracking_id,))
                conn.commit()
                logger.info(f"Marked price tracking record {tracking_id} as complete")
                
        except sqlite3.Error as e:
            logger.error(f"Error marking tracking record as complete: {e}")
            raise

    def get_active_price_tracking(self, trade_id: int) -> Optional[Dict]:
        """
        Get the most recent price tracking record for a trade.
        
        Args:
            trade_id: ID of the trade
        
        Returns:
            Most recent tracking record or None if not found
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                SELECT * FROM option_price_tracking
                WHERE trade_id = ?
                AND tracking_date = DATE('now')
                AND NOT is_complete
                ORDER BY last_update_time DESC
                LIMIT 1
                ''', (trade_id,))
                
                row = cursor.fetchone()
                return dict(row) if row else None
                
        except sqlite3.Error as e:
            logger.error(f"Error retrieving active price tracking: {e}")
            raise

    def get_latest_option_price_data(self, option_symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch the most recent price tracking record for a specific option symbol."""
        sql = """
            SELECT * 
            FROM option_price_tracking 
            WHERE option_symbol = ? 
            ORDER BY tracking_id DESC -- Assuming higher ID means later record
            LIMIT 1
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(sql, (option_symbol,))
                row = cursor.fetchone()
                if row:
                    logger.debug(f"Found latest price data for {option_symbol}")
                    return dict(row) # Convert sqlite3.Row to dict
                else:
                    logger.warning(f"No price data found in DB for {option_symbol}")
                    return None
        except sqlite3.Error as e:
            logger.error(f"Error fetching latest price for {option_symbol}: {e}")
            return None
            
    def get_price_tracking_history(self, trade_id: int, option_symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch price tracking history for a trade, optionally filtering by option symbol."""
        try:
            with self.get_connection() as conn:
                query = '''
                SELECT * FROM option_price_tracking
                WHERE trade_id = ?
                '''
                params = [trade_id]
                
                if option_symbol:
                    query += ' AND option_symbol = ?'
                    params.append(option_symbol)
                    
                query += ' ORDER BY tracking_date ASC, last_update_time ASC'
                
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Error fetching active trades: {e}")
            return [] 