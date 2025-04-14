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
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json

from src.database.db_manager import DatabaseManager
from src.services.price_service import PriceService
from src.config import Config
from ..logging_config import get_logger

# Initialize logger using the helper function
logger = get_logger(__name__)

class DataPipeline:
    """Handles processing and storage of Option Samurai scan results."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None, price_service: Optional[PriceService] = None):
        """Initialize the data pipeline.
        
        Args:
            db_manager: Optional DatabaseManager instance. If None, creates new instance.
            price_service: Optional PriceService instance for real-time pricing.
        """
        self.config = Config()
        self.db = db_manager or DatabaseManager()
        self.price_service = price_service
        
    def calculate_net_credit_or_debit(self, trade_data: Dict[str, Any]) -> Tuple[float, Dict[str, Dict]]:
        """Calculate net credit or debit based on current market prices.
        
        Args:
            trade_data: Dictionary with trade details including option symbols
            
        Returns:
            Tuple of:
            - Net credit (positive) or debit (negative) amount
            - Dictionary of leg prices {
                'short_put': {'bid': X, 'ask': Y, ...},
                'long_put': {'bid': X, 'ask': Y, ...},
                etc.
            }
        """
        if not self.price_service:
            raise ValueError("Price service not available")
            
        leg_prices = {}
        total_net = 0.0
        
        try:
            # Process put legs if present
            if trade_data.get('short_put_symbol') and trade_data.get('long_put_symbol'):
                # Get put leg prices
                short_put = self.price_service.get_option_data(trade_data['short_put_symbol'])
                long_put = self.price_service.get_option_data(trade_data['long_put_symbol'])
                
                if not short_put or not long_put:
                    raise ValueError("Could not get put leg prices from Tradier")
                    
                leg_prices['short_put'] = short_put
                leg_prices['long_put'] = long_put
                
                # Calculate put spread net credit/debit
                # For credit spreads: short bid - long ask (positive)
                # For debit spreads: short ask - long bid (negative)
                put_net = float(short_put['bid']) - float(long_put['ask'])
                total_net += put_net
                logger.info(f"Put spread net: ${put_net:.2f}")
            
            # Process call legs if present
            if trade_data.get('short_call_symbol') and trade_data.get('long_call_symbol'):
                # Get call leg prices
                short_call = self.price_service.get_option_data(trade_data['short_call_symbol'])
                long_call = self.price_service.get_option_data(trade_data['long_call_symbol'])
                
                if not short_call or not long_call:
                    raise ValueError("Could not get call leg prices from Tradier")
                    
                leg_prices['short_call'] = short_call
                leg_prices['long_call'] = long_call
                
                # Calculate call spread net credit/debit
                # For credit spreads: short bid - long ask (positive)
                # For debit spreads: short ask - long bid (negative)
                call_net = float(short_call['bid']) - float(long_call['ask'])
                total_net += call_net
                logger.info(f"Call spread net: ${call_net:.2f}")
            
            logger.info(f"Total net credit/debit: ${total_net:.2f}")
            return total_net, leg_prices
            
        except Exception as e:
            logger.error(f"Error calculating net credit/debit: {e}")
            raise
    
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
            api_data: Raw data from Option Samurai API
            
        Returns:
            Dictionary with trade data in database format
        """
        logger.info("Starting trade data transformation...")
        logger.info(f"Raw API data: {json.dumps(api_data, indent=2)}")
        
        # Extract basic trade info
        symbol_name = api_data.get('name')
        ticker = api_data.get('underlying')
        if not symbol_name or not ticker:
            logger.error("Missing symbol name or ticker in trade data")
            raise ValueError("Missing symbol name or ticker in trade data")
        logger.info(f"Processing trade for symbol: {ticker} ({symbol_name})")
            
        # Get current price
        current_price = float(api_data.get('stock_last', 0))
        logger.info(f"Current price: ${current_price}")
        
        # Parse expiration date
        expiration_dates = api_data.get('expiration_date')
        if not expiration_dates:
            logger.error("Missing expiration date in trade data")
            raise ValueError("Missing expiration date in trade data")
            
        try:
            # Use the first expiration date from the array
            expiration_str = expiration_dates[0]
            expiration_date = datetime.strptime(expiration_str, '%Y-%m-%d').strftime('%Y-%m-%d')
            logger.info(f"Expiration date: {expiration_date}")
        except (ValueError, IndexError) as e:
            logger.error(f"Invalid expiration date format or empty array: {expiration_dates}")
            raise ValueError(f"Invalid expiration date format or empty array: {expiration_dates}")
            
        # Initialize base trade data with all fields set to None
        trade_data = {
            'symbol': symbol_name,
            'ticker': ticker,
            'underlying_price': current_price,
            'expiration_date': expiration_date,
            'theoretical_credit': api_data.get('max_profit', 0),  # Option Samurai's max_profit
            'actual_credit': None,
            'net_credit': api_data.get('max_profit', 0),  # Will be updated if Tradier available
            'entry_price_source': 'optionsamurai',  # Will be updated if Tradier available
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
        logger.info(f"Initialized base trade data: {json.dumps(trade_data, indent=2)}")
        
        # Determine strategy and map strikes accordingly
        try:
            strategy = self._determine_strategy(api_data)
            trade_data['trade_type'] = strategy
            logger.info(f"Determined strategy: {strategy}")
        except ValueError as e:
            logger.error(f"Error determining strategy: {e}")
            raise
            
        # Map strikes based on strategy
        try:
            if strategy == 'BULL_PUT':
                logger.info("Mapping bull put strikes...")
                self._map_bull_put_strikes(trade_data, api_data)
            elif strategy == 'BEAR_CALL':
                logger.info("Mapping bear call strikes...")
                self._map_bear_call_strikes(trade_data, api_data)
            elif strategy == 'IRON_CONDOR':
                logger.info("Mapping iron condor strikes...")
                self._map_iron_condor_strikes(trade_data, api_data)
            elif strategy == 'BULL_CALL':
                logger.info("Mapping bull call strikes...")
                self._map_bull_call_strikes(trade_data, api_data)
            elif strategy == 'BEAR_PUT':
                logger.info("Mapping bear put strikes...")
                self._map_bear_put_strikes(trade_data, api_data)
            else:
                logger.error(f"Unknown strategy type: {strategy}")
                raise ValueError(f"Unknown strategy type: {strategy}")
            logger.info(f"Strike mapping complete. Updated trade data: {json.dumps(trade_data, indent=2)}")
        except Exception as e:
            logger.error(f"Error mapping strikes: {e}")
            raise
            
        # If we have price service available, get realistic credit/debit
        if self.price_service:
            try:
                logger.info("Calculating net credit/debit using price service...")
                net_credit_or_debit, leg_prices = self.calculate_net_credit_or_debit(trade_data)
                trade_data['actual_credit'] = net_credit_or_debit
                trade_data['net_credit'] = net_credit_or_debit  # Use realistic credit/debit as net
                trade_data['entry_price_source'] = 'tradier'
                logger.info(f"Using Tradier prices for {symbol_name}: ${net_credit_or_debit:.2f}")
            except Exception as e:
                logger.warning(f"Could not get Tradier prices for {symbol_name}, using Option Samurai credit: {e}")
                # Keep the Option Samurai values we set initially
        
        logger.info("Trade data transformation complete")
        return trade_data
    
    def _map_bull_put_strikes(self, trade_data: Dict[str, Any], api_data: Dict[str, Any]):
        """Map bull put strikes to trade data."""
        strikes = api_data.get('strike', [])
        if not strikes:
            raise ValueError("No strike prices found in trade data")
            
        if len(strikes) != 2:
            raise ValueError(f"Bull Put requires 2 strikes, got {len(strikes)}")
            
        trade_data.update({
            'short_put': strikes[0],
            'long_put': strikes[1],
            'short_put_symbol': self._build_option_symbol(trade_data['ticker'], trade_data['expiration_date'], strikes[0], 'P'),
            'long_put_symbol': self._build_option_symbol(trade_data['ticker'], trade_data['expiration_date'], strikes[1], 'P')
        })
    
    def _map_bear_call_strikes(self, trade_data: Dict[str, Any], api_data: Dict[str, Any]):
        """Map bear call strikes to trade data."""
        strikes = api_data.get('strike', [])
        if not strikes:
            raise ValueError("No strike prices found in trade data")
            
        if len(strikes) != 2:
            raise ValueError(f"Bear Call requires 2 strikes, got {len(strikes)}")
            
        trade_data.update({
            'short_call': strikes[0],
            'long_call': strikes[1],
            'short_call_symbol': self._build_option_symbol(trade_data['ticker'], trade_data['expiration_date'], strikes[0], 'C'),
            'long_call_symbol': self._build_option_symbol(trade_data['ticker'], trade_data['expiration_date'], strikes[1], 'C')
        })
    
    def _map_iron_condor_strikes(self, trade_data: Dict[str, Any], api_data: Dict[str, Any]):
        """Map iron condor strikes to trade data."""
        strikes = api_data.get('strike', [])
        if not strikes:
            raise ValueError("No strike prices found in trade data")
            
        if len(strikes) != 4:
            raise ValueError(f"Iron Condor requires 4 strikes, got {len(strikes)}")
            
        trade_data.update({
            'short_put': strikes[0],
            'long_put': strikes[1],
            'short_call': strikes[2],
            'long_call': strikes[3],
            'short_put_symbol': self._build_option_symbol(trade_data['ticker'], trade_data['expiration_date'], strikes[0], 'P'),
            'long_put_symbol': self._build_option_symbol(trade_data['ticker'], trade_data['expiration_date'], strikes[1], 'P'),
            'short_call_symbol': self._build_option_symbol(trade_data['ticker'], trade_data['expiration_date'], strikes[2], 'C'),
            'long_call_symbol': self._build_option_symbol(trade_data['ticker'], trade_data['expiration_date'], strikes[3], 'C')
        })
    
    def _map_bull_call_strikes(self, trade_data: Dict[str, Any], api_data: Dict[str, Any]) -> None:
        """Map strikes for bull call spread strategy.
        
        Args:
            trade_data: Trade data dictionary to update
            api_data: Raw data from Option Samurai API
        """
        strikes = api_data.get('strike', [])
        if len(strikes) != 2:
            raise ValueError(f"Bull call spread requires exactly 2 strikes, got {len(strikes)}")
            
        # Sort strikes to ensure correct mapping
        strikes.sort()
        
        # For bull call spread:
        # - Buy lower strike call (long_call)
        # - Sell higher strike call (short_call)
        trade_data['long_call'] = strikes[0]
        trade_data['short_call'] = strikes[1]
        
        # Get option symbols using ticker
        trade_data['long_call_symbol'] = self._build_option_symbol(
            trade_data['ticker'],
            trade_data['expiration_date'],
            trade_data['long_call'],
            'C'
        )
        trade_data['short_call_symbol'] = self._build_option_symbol(
            trade_data['ticker'],
            trade_data['expiration_date'],
            trade_data['short_call'],
            'C'
        )
    
    def _map_bear_put_strikes(self, trade_data: Dict[str, Any], api_data: Dict[str, Any]) -> None:
        """Map strikes for bear put spread strategy.
        
        Args:
            trade_data: Trade data dictionary to update
            api_data: Raw data from Option Samurai API
        """
        strikes = api_data.get('strike', [])
        if len(strikes) != 2:
            raise ValueError(f"Bear put spread requires exactly 2 strikes, got {len(strikes)}")
            
        # Sort strikes to ensure correct mapping
        strikes.sort()
        
        # For bear put spread:
        # - Buy lower strike put (long_put)
        # - Sell higher strike put (short_put)
        trade_data['long_put'] = strikes[0]
        trade_data['short_put'] = strikes[1]
        
        # Get option symbols using ticker
        trade_data['long_put_symbol'] = self._build_option_symbol(
            trade_data['ticker'],
            trade_data['expiration_date'],
            trade_data['long_put'],
            'P'
        )
        trade_data['short_put_symbol'] = self._build_option_symbol(
            trade_data['ticker'],
            trade_data['expiration_date'],
            trade_data['short_put'],
            'P'
        )
    
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