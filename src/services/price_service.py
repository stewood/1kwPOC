"""
Price Service for fetching real-time market data.

This module provides functionality to fetch current market prices and option data
using the Tradier API. It includes basic caching to prevent excessive API calls.
"""

import logging
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
from functools import lru_cache
import re
from .tradier_client import TradierClient
from ..config import Config
from ..logging_config import get_logger

# Initialize logger using the helper function
logger = get_logger(__name__)

class PriceService:
    """Service for fetching real-time market data using Tradier."""
    
    def __init__(self, cache_timeout: int = 60):
        """
        Initialize the price service.
        
        Args:
            cache_timeout (int): Number of seconds to cache price data for. Defaults to 60.
        """
        self.cache_timeout = cache_timeout
        self.config = Config()
        
        if not self.config.tradier_token:
            raise ValueError("TRADIER_TOKEN environment variable not set")
            
        logger.debug("Initializing Tradier client...")
        self.client = TradierClient(
            token=self.config.tradier_token,
            use_sandbox=self.config.tradier_sandbox
        )
        logger.debug("Tradier client initialized successfully")
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get the current price for a symbol.
        Handles potential errors in the response structure.
        
        Args:
            symbol: The symbol to get the price for
            
        Returns:
            Current price as a float, or None if unavailable/error.
        """
        try:
            logger.info(f"Getting current quote for {symbol}...")
            response = self.client.get_quotes(symbol)
            logger.debug(f"Raw Tradier quote response for {symbol}: {response}")
            
            # Check response structure carefully
            if response and isinstance(response, dict) and 'quotes' in response:
                quotes_data = response['quotes']
                if quotes_data and isinstance(quotes_data, dict) and 'quote' in quotes_data:
                    quote = quotes_data['quote']
                    # Handle case where single quote is not a list
                    if isinstance(quote, list):
                        # If multiple symbols were somehow requested/returned, find the right one
                        target_quote = next((q for q in quote if q.get('symbol') == symbol), None)
                    elif isinstance(quote, dict) and quote.get('symbol') == symbol:
                        target_quote = quote
                    else:
                        target_quote = None
                        
                    if target_quote and 'last' in target_quote and target_quote['last'] is not None:
                        price = float(target_quote['last'])
                        logger.info(f"Successfully retrieved current price for {symbol}: {price}")
                        return price
                    else:
                        logger.warning(f"Could not extract 'last' price from quote for {symbol}. Quote data: {target_quote}")
                        return None
                else:
                     logger.warning(f"'quote' key missing or invalid in quotes data for {symbol}. Quotes data: {quotes_data}")
                     return None
            else:
                logger.warning(f"Unexpected response structure or missing 'quotes' key for {symbol}. Full response: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {str(e)}", exc_info=True)
            return None
    
    def get_historical_price(self, symbol: str, date: str) -> Optional[float]:
        """
        Get the historical price for a symbol on a specific date.
        
        Args:
            symbol: The symbol to get the price for
            date: The date in YYYY-MM-DD format
            
        Returns:
            Historical price as a float, or None if no data available
        """
        try:
            logger.info(f"Getting historical price for {symbol} on {date}")
            history = self.client.get_history(symbol, date)
            
            # Log the complete response structure
            logger.debug(f"Raw history response structure: {history}")
            
            if not history:
                logger.warning(f"No history response for {symbol} on {date}")
                return None
                
            if not history.get('history'):
                logger.warning(f"Response missing 'history' key. Full response: {history}")
                return None
                
            day_data = history['history'].get('day')
            if not day_data:
                logger.warning(f"No daily data found in history['history']['day']. History structure: {history['history']}")
                return None
                
            # Log what we found in a structured way
            logger.info(f"Found historical data for {symbol}:")
            logger.info("Daily data:")
            for key, value in day_data.items():
                logger.info(f"  {key}: {value}")
                
            return float(day_data['close'])
            
        except Exception as e:
            logger.error(f"Error getting historical price for {symbol} on {date}: {str(e)}")
            logger.exception("Full traceback:")
            return None
    
    def get_current_prices(self, symbols: List[str]) -> Dict[str, Optional[float]]:
        """Get current prices for multiple symbols.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dictionary mapping symbols to their current prices
        """
        try:
            response = self.client.get_quotes(symbols)
            prices = {}
            if 'quotes' in response and 'quote' in response['quotes']:
                quotes = response['quotes']['quote']
                if not isinstance(quotes, list):
                    quotes = [quotes]  # Handle single quote case
                for quote in quotes:
                    symbol = quote.get('symbol')
                    if symbol:
                        prices[symbol] = float(quote.get('last', 0))
            return prices
        except Exception as e:
            logger.error(f"Error getting prices: {str(e)}")
            return {symbol: None for symbol in symbols}
    
    def get_option_data(self, option_symbol: str) -> Optional[Dict[str, Any]]:
        """Get current option data from Tradier.
        
        Args:
            option_symbol: OCC option symbol (e.g., 'MSFT250516C00340000')
            
        Returns:
            Dictionary containing option data or None if not available
        """
        try:
            logger.info(f"\n🔍 Processing option symbol: {option_symbol}")
            
            # Extract ticker and option details using regex
            # Format: SYMBOL + YYMMDD + [C|P] + STRIKE
            match = re.match(r'^([A-Z]+)(\d{6})([CP])(\d+)$', option_symbol)
            if not match:
                logger.error(f"  ❌ Could not parse option symbol: {option_symbol}")
                logger.error(f"  • Expected format: SYMBOL + YYMMDD + [C|P] + STRIKE")
                return None
                
            ticker, date_str, option_type, strike_str = match.groups()
            
            # Format date from YYMMDD to YYYY-MM-DD
            year = int("20" + date_str[0:2])
            month = int(date_str[2:4])
            day = int(date_str[4:6])
            expiration_date = f"{year}-{month:02d}-{day:02d}"
            
            # Convert strike string to decimal
            strike = float(strike_str) / 1000
            
            logger.info(f"  📅 Parsed option details:")
            logger.info(f"    • Ticker: {ticker}")
            logger.info(f"    • Expiration: {expiration_date}")
            logger.info(f"    • Type: {'Call' if option_type == 'C' else 'Put'}")
            logger.info(f"    • Strike: ${strike:.2f}")
            
            # Get market status
            market_status = self.client.get_market_clock()
            
            # Get option chain for the expiration date
            logger.info(f"  🌐 Fetching option chain for {ticker}...")
            chain_response = self.client.get_option_chains(ticker, expiration_date)
            
            if not chain_response.get('options', {}).get('option'):
                logger.error(f"  ❌ No option chain data available for {ticker}")
                return None
            
            # Find our specific option in the chain
            chain = chain_response['options']['option']
            if not isinstance(chain, list):
                chain = [chain]  # Handle single option case
                
            # Find the matching option
            option_row = None
            for option in chain:
                if (option.get('option_type', '').lower()[0] == option_type.lower() and 
                    abs(float(option.get('strike', 0)) - strike) < 0.01):
                    option_row = option
                    break
            
            if not option_row:
                logger.error(f"  ❌ Could not find matching option in chain")
                return None
            
            # Transform into our format
            result = {
                'bid': option_row.get('bid'),
                'ask': option_row.get('ask'),
                'last': option_row.get('last'),
                'mark': (float(option_row.get('bid', 0)) + float(option_row.get('ask', 0))) / 2,
                'bid_size': option_row.get('bid_size'),
                'ask_size': option_row.get('ask_size'),
                'volume': option_row.get('volume'),
                'open_interest': option_row.get('open_interest'),
                'exchange': option_row.get('exchange'),
                
                # Greeks data if available
                'greeks_update_time': datetime.now().isoformat(),
                'delta': option_row.get('delta'),
                'gamma': option_row.get('gamma'),
                'theta': option_row.get('theta'),
                'vega': option_row.get('vega'),
                'rho': option_row.get('rho'),
                'phi': None,  # Not provided by Tradier
                
                # IV data from the chain if available
                'bid_iv': option_row.get('bid_iv'),
                'mid_iv': option_row.get('mid_iv'),
                'ask_iv': option_row.get('ask_iv'),
                'smv_vol': option_row.get('smv_vol'),
                
                # Contract details
                'contract_size': option_row.get('contract_size', 100),
                'expiration_type': option_row.get('expiration_type', 'regular'),
                'is_closing_only': option_row.get('is_closing_only', False),
                'is_tradeable': option_row.get('is_tradeable', True),
                
                # Market status from clock endpoint
                'is_market_closed': market_status.get('clock', {}).get('state') not in ['open', 'premarket', 'postmarket']
            }
            
            logger.info(f"  ✅ Successfully retrieved option data")
            logger.info(f"    • Bid/Ask: ${result['bid']:.2f}/${result['ask']:.2f}")
            logger.info(f"    • Volume: {result['volume']}")
            logger.info(f"    • Open Interest: {result['open_interest']}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error fetching option data for {option_symbol}: {str(e)}", exc_info=True)
            return None
    
    def get_market_status(self) -> Dict[str, Any]:
        """
        Get the current market status from Tradier.
        
        Returns:
            Dict containing market status information:
            - state: 'open', 'closed', 'premarket', or 'postmarket'
            - description: Human readable description
            - next_state: Next market state
            - next_change: Time of next state change
        """
        try:
            return self.client.get_market_clock()
        except Exception as e:
            logger.error(f"Error getting market status: {str(e)}")
            return {
                'clock': {
                    'state': 'unknown',
                    'description': 'Error getting market status',
                    'next_state': None,
                    'next_change': None
                }
            }

# Example usage:
if __name__ == '__main__':
    price_service = PriceService()
    
    # Get single price
    spy_price = price_service.get_current_price('SPY')
    print(f"SPY price: ${spy_price}")
    
    # Get multiple prices
    prices = price_service.get_current_prices(['SPY', 'QQQ', 'IWM'])
    print("\nMarket prices:")
    for symbol, price in prices.items():
        print(f"{symbol}: ${price}")
    
    # Get option chain
    print("\nFetching SPY options:")
    spy_options = price_service.get_option_data('SPY340')
    if spy_options:
        print(f"Expiration date: {spy_options['expiration_date']}")
        print(f"Bid/Ask: ${spy_options['bid']:.2f}/${spy_options['ask']:.2f}")
        print(f"Volume: {spy_options['volume']}")
        print(f"Open Interest: {spy_options['open_interest']}")
        print(f"Market status: {spy_options['market_status']}") 