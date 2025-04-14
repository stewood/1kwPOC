import logging
from typing import Dict, List, Optional, Any, Union
import requests
from datetime import datetime
from ..logging_config import get_logger

# Initialize logger using the helper function
logger = get_logger(__name__)

class TradierClient:
    """Client for interacting with Tradier's API directly."""
    
    def __init__(self, token: str, use_sandbox: bool = False):
        """
        Initialize the Tradier API client.
        
        Args:
            token: Tradier API token
            use_sandbox: Whether to use sandbox environment (default: False)
        """
        self.token = token
        self.base_url = "https://sandbox.tradier.com/v1" if use_sandbox else "https://api.tradier.com/v1"
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json'
        }
        logger.debug(f"Initialized Tradier client with {'sandbox' if use_sandbox else 'production'} environment")
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make a request to the Tradier API.
        
        Args:
            method: HTTP method (GET, POST, etc)
            endpoint: API endpoint (e.g. '/v1/markets/quotes')
            params: Optional query parameters
            
        Returns:
            API response as dictionary
            
        Raises:
            requests.exceptions.RequestException: If the request fails
        """
        url = f"{self.base_url}{endpoint}"
        try:
            logger.debug(f"Making {method} request to {url} with params: {params}")
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            response_data = response.json()
            logger.debug(f"Received response from Tradier API: {response_data}")
            return response_data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to {url}: {str(e)}")
            raise
    
    def get_quotes(self, symbols: Union[str, List[str]]) -> Dict:
        """
        Get quotes for one or more symbols.
        
        Args:
            symbols: A single symbol string or a list of symbol strings.
            
        Returns:
            Dictionary containing quote data
        """
        if isinstance(symbols, list):
            symbols_param = ','.join(symbols)
        else:
            symbols_param = symbols

        return self._make_request(
            'GET',
            '/markets/quotes',
            params={'symbols': symbols_param}
        )
    
    def get_option_chains(self, symbol: str, expiration: str) -> Dict:
        """
        Get option chain data for a symbol.
        
        Args:
            symbol: The underlying symbol
            expiration: Expiration date (YYYY-MM-DD)
            
        Returns:
            Dictionary containing option chain data
        """
        return self._make_request(
            'GET',
            '/markets/options/chains',
            params={
                'symbol': symbol,
                'expiration': expiration,
                'greeks': 'true'
            }
        )
    
    def get_option_expirations(self, symbol: str) -> Dict:
        """
        Get expiration dates for a symbol's options.
        
        Args:
            symbol: The underlying symbol
            
        Returns:
            Dictionary containing expiration dates
        """
        return self._make_request(
            'GET',
            '/markets/options/expirations',
            params={
                'symbol': symbol,
                'includeAllRoots': 'true',
                'strikes': 'false'
            }
        )
    
    def get_option_strikes(self, symbol: str, expiration: str) -> Dict:
        """
        Get strike prices for a symbol's options.
        
        Args:
            symbol: The underlying symbol
            expiration: Expiration date (YYYY-MM-DD)
            
        Returns:
            Dictionary containing strike prices
        """
        return self._make_request(
            'GET',
            '/markets/options/strikes',
            params={
                'symbol': symbol,
                'expiration': expiration
            }
        )
    
    def lookup_option_symbols(self, underlying: str) -> Dict:
        """
        Look up option symbols for an underlying.
        
        Args:
            underlying: The underlying symbol
            
        Returns:
            Dictionary containing option symbols
        """
        return self._make_request(
            'GET',
            '/markets/options/lookup',
            params={'underlying': underlying}
        )
    
    def get_market_clock(self) -> Dict:
        """
        Get the market clock.
        
        Returns:
            Dictionary containing market status information
        """
        return self._make_request('GET', '/markets/clock')

    def get_history(self, symbol: str, date: str) -> Dict:
        """
        Get historical price data for a symbol on a specific date.
        
        Args:
            symbol: The symbol to get history for
            date: The date in YYYY-MM-DD format
            
        Returns:
            Dictionary containing historical price data for the specified date
        """
        return self._make_request(
            'GET',
            '/markets/history',
            params={
                'symbol': symbol,
                'start': date,
                'end': date,
                'interval': 'daily'
            }
        ) 