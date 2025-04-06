"""
Price Service for fetching real-time market data.

This module provides functionality to fetch current market prices and option data
using the Tradier API. It includes basic caching to prevent excessive API calls.
"""

import logging
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
from functools import lru_cache
import pandas as pd
from uvatradier import Quotes, OptionsData
from ..config import Config

# Configure logging
logging.basicConfig(level=logging.DEBUG)  # Set to DEBUG for more detailed logs
logger = logging.getLogger(__name__)

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
            
        logger.debug("Initializing Tradier clients...")
        # Initialize Tradier clients
        self.quotes = Quotes(None, self.config.tradier_token)
        self.options = OptionsData(None, self.config.tradier_token)
        logger.debug("Tradier clients initialized successfully")
    
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
            logger.debug(f"Fetching quote for {symbol}...")
            quote_df = self.quotes.get_quote_day(symbol)
            logger.debug(f"Quote data received for {symbol}: {quote_df}")
            
            if quote_df.empty:
                logger.error(f"No quote data returned for {symbol}")
                return None
                
            # Extract the last price from the quote DataFrame
            price = float(quote_df['last'].iloc[0])
            logger.debug(f"Extracted price for {symbol}: ${price}")
            return price
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}", exc_info=True)
            return None
    
    def get_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """
        Get current prices for multiple symbols.
        
        Args:
            symbols (List[str]): List of stock symbols
            
        Returns:
            Dict[str, float]: Dictionary of symbol -> price mappings
        """
        try:
            logger.debug(f"Fetching quotes for {symbols}...")
            quotes_df = self.quotes.get_quote_data(symbols)
            logger.debug(f"Quote data received: {quotes_df}")
            
            if quotes_df.empty:
                logger.error("No quote data returned")
                return {symbol: None for symbol in symbols}
            
            # Format response
            result = {
                symbol: float(row['last'])
                for symbol, row in quotes_df.iterrows()
                if pd.notna(row['last'])
            }
            logger.debug(f"Formatted prices: {result}")
            return result
        except Exception as e:
            logger.error(f"Error fetching prices for {symbols}: {e}", exc_info=True)
            return {symbol: None for symbol in symbols}
    
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
            # Get available expirations if none provided
            if not expiration_date:
                logger.debug(f"Fetching expiration dates for {symbol}...")
                expirations = self.options.get_expiry_dates(symbol)
                logger.debug(f"Expiration dates received: {expirations}")
                
                if not isinstance(expirations, list):
                    expirations = expirations.tolist()
                
                if not expirations:  # Check if list is empty
                    logger.error(f"No option expirations available for {symbol}")
                    return None
                expiration_date = expirations[0]  # Get first expiration date
                logger.debug(f"Selected expiration date: {expiration_date}")
            
            # Get option chain
            logger.debug(f"Fetching option chain for {symbol}...")
            chain_df = self.options.get_chain_day(symbol)
            logger.debug(f"Option chain received: {chain_df}")
            
            if chain_df.empty:
                logger.error(f"No option chain data for {symbol} at {expiration_date}")
                return None
            
            # Convert DataFrame to dictionary format
            chain_dict = chain_df.to_dict('records')
            
            # Format response to match expected structure
            result = {
                'expiration': expiration_date,
                'calls': [
                    {
                        'strike': float(opt['strike']),
                        'bid': float(opt['bid']),
                        'ask': float(opt['ask']),
                        'volume': int(opt.get('volume', 0)),
                        'open_interest': int(opt.get('open_interest', 0))
                    }
                    for opt in chain_dict
                    if opt.get('option_type') == 'call'
                ],
                'puts': [
                    {
                        'strike': float(opt['strike']),
                        'bid': float(opt['bid']),
                        'ask': float(opt['ask']),
                        'volume': int(opt.get('volume', 0)),
                        'open_interest': int(opt.get('open_interest', 0))
                    }
                    for opt in chain_dict
                    if opt.get('option_type') == 'put'
                ]
            }
            logger.debug(f"Formatted option chain: {result}")
            return result
        except Exception as e:
            logger.error(f"Error fetching option chain for {symbol}: {e}", exc_info=True)
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
    
    # Get option chain
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