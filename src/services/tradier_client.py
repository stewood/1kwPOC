import logging
from typing import Dict, List, Optional, Any
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

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
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to {url}: {str(e)}")
            raise
    
    def get_quotes(self, symbols: List[str]) -> Dict:
        """
        Get quotes for one or more symbols.
        
        Args:
            symbols: List of symbols to get quotes for
            
        Returns:
            Dictionary containing quote data
        """
        return self._make_request(
            'GET',
            '/markets/quotes',
            params={'symbols': ','.join(symbols)}
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