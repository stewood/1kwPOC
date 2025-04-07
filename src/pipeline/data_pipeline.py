"""
Data Pipeline Module

Handles the transformation and storage of Option Samurai data into the database.
Implements:
- Data transformation from API format to database schema
- Duplicate detection
- Basic validation
- Performance monitoring
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.database.db_manager import DatabaseManager
from src.config import Config

logger = logging.getLogger(__name__)

class DataPipeline:
    """Handles processing and storage of Option Samurai scan results."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize the data pipeline.
        
        Args:
            db_manager: Optional DatabaseManager instance. If None, creates new instance.
        """
        self.config = Config()
        self.db = db_manager or DatabaseManager()
        
    def process_scan_results(self, results: Dict[str, Any], scan_name: str) -> List[int]:
        """Process scan results and store valid trades in database.
        
        Args:
            results: Raw scan results from Option Samurai API
            scan_name: Name of the scan for logging
            
        Returns:
            List of trade IDs for successfully stored trades
        """
        logger.info(f"Processing scan results from: {scan_name}")
        start_time = datetime.now()
        
        stored_trades = []
        items = results.get('items', [])
        
        if not items:
            logger.warning(f"No items found in scan results: {scan_name}")
            return []
            
        logger.info(f"Found {len(items)} potential trades to process")
        
        for item in items:
            try:
                # Skip if we already have this trade
                if self._is_duplicate_trade(item):
                    symbol = item.get('name', 'Unknown')
                    strategy = self._determine_strategy(item)
                    logger.info(f"Skipping duplicate trade: {symbol} {strategy}")
                    continue
                
                # Transform API data to database format
                trade_data = self._transform_trade_data(item)
                
                # Store in database
                trade_id = self.db.save_new_trade(trade_data)
                stored_trades.append(trade_id)
                logger.info(f"Stored trade {trade_id}: {trade_data['symbol']} {trade_data['trade_type']}")
                
            except Exception as e:
                symbol = item.get('name', 'Unknown')
                logger.error(f"Error processing trade for {symbol}: {e}", exc_info=True)
                continue
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Processed {len(items)} trades in {duration:.2f} seconds")
        logger.info(f"Successfully stored {len(stored_trades)} new trades")
        
        return stored_trades
    
    def _is_duplicate_trade(self, trade_data: Dict[str, Any]) -> bool:
        """Check if we already have an active trade for this symbol and strategy combination.
        
        We allow one active trade per underlying symbol per strategy type.
        For example, we can have both a BULL_PUT and an IRON_CONDOR on SPY,
        but not two BULL_PUTs on SPY.
        
        Args:
            trade_data: Raw trade data from Option Samurai API
            
        Returns:
            True if we already have an active trade for this symbol and strategy
        """
        symbol = trade_data.get('name')
        if not symbol:
            return False
            
        try:
            strategy = self._determine_strategy(trade_data)
        except ValueError:
            return False  # If we can't determine strategy, assume not duplicate
            
        # Get active trades and check if we have any for this symbol and strategy
        active_trades = self.db.get_active_trades()
        return any(t['symbol'] == symbol and t['trade_type'] == strategy for t in active_trades)
    
    def _determine_strategy(self, trade_data: Dict[str, Any]) -> str:
        """Determine the trade strategy from Option Samurai data.
        
        Args:
            trade_data: Raw trade data from Option Samurai API
            
        Returns:
            Strategy type (BULL_PUT, BEAR_CALL, or IRON_CONDOR)
            
        Raises:
            ValueError: If strategy cannot be determined
        """
        strikes = trade_data.get('strike', [])
        if not strikes:
            raise ValueError("No strike prices found in trade data")
            
        # Iron Condor has 4 strikes
        if len(strikes) == 4:
            return 'IRON_CONDOR'
            
        # Vertical spreads have 2 strikes
        elif len(strikes) == 2:
            # If first strike is lower than second, it's a bull put spread
            if strikes[0] < strikes[1]:
                return 'BULL_PUT'
            else:
                return 'BEAR_CALL'
                
        raise ValueError(f"Unexpected number of strikes: {len(strikes)}")
    
    def _transform_trade_data(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Option Samurai API data to database format.
        
        Args:
            api_data: Raw trade data from Option Samurai API
            
        Returns:
            Dictionary matching database schema for active_trades
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        symbol = api_data.get('underlying')
        if not symbol:
            raise ValueError("Missing required field: underlying (ticker symbol)")
            
        # Get current price and validate
        current_price = api_data.get('stock_last')
        if not current_price:
            raise ValueError(f"Missing current price for {symbol}")
            
        # Get expiration and validate
        expiration = api_data.get('expiration_date', [])
        if not expiration:
            raise ValueError(f"Missing expiration date for {symbol}")
        expiration_date = expiration[0]  # Use first expiration if multiple
        
        # Get strikes and validate
        strikes = api_data.get('strike', [])
        if not strikes:
            raise ValueError(f"Missing strike prices for {symbol}")
            
        # Initialize base trade data with all fields set to None
        trade_data = {
            'symbol': symbol,
            'underlying_price': current_price,
            'expiration_date': expiration_date,
            'net_credit': api_data.get('max_profit', 0),  # Max profit is our credit
            'num_contracts': 1,  # Default to 1 contract
            'short_put': None,
            'long_put': None,
            'short_put_symbol': None,
            'long_put_symbol': None,
            'short_call': None,
            'long_call': None,
            'short_call_symbol': None,
            'long_call_symbol': None
        }
        
        # Determine strategy and map strikes accordingly
        strategy = self._determine_strategy(api_data)
        trade_data['trade_type'] = strategy
        
        if strategy == 'IRON_CONDOR':
            if len(strikes) != 4:
                raise ValueError(f"Iron Condor requires 4 strikes, got {len(strikes)}")
            trade_data.update({
                'short_put': strikes[0],
                'long_put': strikes[1],
                'short_call': strikes[2],
                'long_call': strikes[3],
                'short_put_symbol': self._build_option_symbol(symbol, expiration_date, strikes[0], 'P'),
                'long_put_symbol': self._build_option_symbol(symbol, expiration_date, strikes[1], 'P'),
                'short_call_symbol': self._build_option_symbol(symbol, expiration_date, strikes[2], 'C'),
                'long_call_symbol': self._build_option_symbol(symbol, expiration_date, strikes[3], 'C')
            })
        elif strategy == 'BULL_PUT':
            if len(strikes) != 2:
                raise ValueError(f"Bull Put requires 2 strikes, got {len(strikes)}")
            trade_data.update({
                'short_put': strikes[0],
                'long_put': strikes[1],
                'short_put_symbol': self._build_option_symbol(symbol, expiration_date, strikes[0], 'P'),
                'long_put_symbol': self._build_option_symbol(symbol, expiration_date, strikes[1], 'P')
            })
        elif strategy == 'BEAR_CALL':
            if len(strikes) != 2:
                raise ValueError(f"Bear Call requires 2 strikes, got {len(strikes)}")
            trade_data.update({
                'short_call': strikes[0],
                'long_call': strikes[1],
                'short_call_symbol': self._build_option_symbol(symbol, expiration_date, strikes[0], 'C'),
                'long_call_symbol': self._build_option_symbol(symbol, expiration_date, strikes[1], 'C')
            })
            
        return trade_data
    
    def _build_option_symbol(self, symbol: str, expiration: str, strike: float, option_type: str) -> str:
        """Build OCC option symbol.
        
        Args:
            symbol: Underlying symbol
            expiration: Expiration date (YYYY-MM-DD)
            strike: Strike price
            option_type: 'P' for put or 'C' for call
            
        Returns:
            OCC option symbol (e.g., 'SPY240419P410000')
        """
        # Convert YYYY-MM-DD to YYMMDD
        exp_date = datetime.strptime(expiration, '%Y-%m-%d')
        exp_str = exp_date.strftime('%y%m%d')
        
        # Convert strike to padded integer (multiply by 1000 and remove decimal)
        strike_str = f"{int(strike * 1000):08d}"
        
        return f"{symbol}{exp_str}{option_type}{strike_str}" 