"""
Price Service for fetching real-time market data.

This module provides functionality to fetch current market prices and option data
using the yfinance library. It includes basic caching to prevent excessive API calls.
"""

import yfinance as yf
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
import logging
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PriceService:
    """Service for fetching real-time market data using yfinance."""
    
    def __init__(self, cache_timeout: int = 60):
        """
        Initialize the price service.
        
        Args:
            cache_timeout (int): Number of seconds to cache price data for. Defaults to 60.
        """
        self.cache_timeout = cache_timeout
    
    @lru_cache(maxsize=100)
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get the current price for a symbol.
        Uses LRU cache to prevent excessive API calls.
        
        Args:
            symbol (str): The stock symbol to get price for
            
        Returns:
            Optional[float]: Current price or None if unavailable
            
        Raises:
            ValueError: If symbol is invalid
        """
        try:
            ticker = yf.Ticker(symbol)
            return ticker.info.get('regularMarketPrice')
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None
    
    def get_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """
        Get current prices for multiple symbols.
        
        Args:
            symbols (List[str]): List of stock symbols
            
        Returns:
            Dict[str, float]: Dictionary of symbol -> price mappings
        """
        return {
            symbol: self.get_current_price(symbol)
            for symbol in symbols
        }
    
    def get_option_chain(self, symbol: str, expiration_date: Optional[str] = None) -> Optional[Dict]:
        """
        Get option chain data for a symbol and expiration date.
        
        Args:
            symbol (str): The stock symbol
            expiration_date (str, optional): Option expiration date in YYYY-MM-DD format.
                                           If None, uses the first available expiration.
            
        Returns:
            Optional[Dict]: Option chain data or None if unavailable
        """
        try:
            ticker = yf.Ticker(symbol)
            
            # Get available expirations
            expirations = ticker.options
            
            if not expirations:
                logger.error(f"No option expirations available for {symbol}")
                return None
                
            # Use provided date or first available
            exp_date = expiration_date or expirations[0]
            
            if exp_date not in expirations:
                logger.error(f"Expiration {exp_date} not available for {symbol}. Available dates: {expirations}")
                return None
            
            options = ticker.option_chain(exp_date)
            return {
                'expiration': exp_date,
                'calls': options.calls.to_dict('records'),
                'puts': options.puts.to_dict('records')
            }
        except Exception as e:
            logger.error(f"Error fetching option chain for {symbol}: {e}")
            return None
    
    def clear_cache(self):
        """Clear the price cache."""
        self.get_current_price.cache_clear()

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
    
    # Get option chain using first available expiration
    print("\nFetching SPY options:")
    spy_options = price_service.get_option_chain('SPY')
    if spy_options:
        print(f"Expiration date: {spy_options['expiration']}")
        print(f"Number of calls: {len(spy_options['calls'])}")
        print(f"Number of puts: {len(spy_options['puts'])}")
        
        # Show first few call options
        print("\nSample call options (first 3):")
        for call in spy_options['calls'][:3]:
            print(f"Strike: ${call['strike']}, Bid: ${call['bid']}, Ask: ${call['ask']}") 