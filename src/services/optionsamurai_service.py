"""
Option Samurai Service Module

Provides integration with Option Samurai API for scan operations and token management.
This module handles:
- API token management
- Scan listing and execution
- Error handling and logging
"""

import os
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from optionsamurai_api import APIClient

class OptionSamuraiService:
    """Service for interacting with Option Samurai API
    
    This service provides a simplified interface to the Option Samurai API,
    handling token management, scan operations, and error cases.
    
    Attributes:
        _client (Optional[APIClient]): The underlying API client instance
    """
    
    def __init__(self):
        """Initialize the service and load token from environment
        
        Attempts to load the OPTIONSAMURAI_BEARER_TOKEN from environment
        variables. If found, initializes the API client with this token.
        """
        load_dotenv()  # Load .env file if exists
        self._client: Optional[APIClient] = None
        
        # Try to initialize with token from environment
        token = os.getenv("OPTIONSAMURAI_BEARER_TOKEN")
        if token:
            self.set_token(token)
    
    def set_token(self, token: str) -> bool:
        """Set API token without validation
        
        Args:
            token (str): The bearer token to use for API authentication
            
        Returns:
            bool: True if token was set successfully, False if an error occurred
            
        Note:
            This method does not validate the token format or expiration.
            It only ensures the client can be initialized with the token.
        """
        try:
            self._client = APIClient(bearer_token=token)
            return True
        except Exception as e:
            print(f"Error setting token: {e}")
            self._client = None
            return False
    
    def list_scans(self) -> List[Dict[str, Any]]:
        """Get list of available saved scans
        
        Returns:
            List[Dict[str, Any]]: List of scan information dictionaries.
            Returns empty list if client is not initialized or an error occurs.
            
        Note:
            Each scan dictionary contains:
            - id: Unique identifier for the scan
            - label: Human-readable name of the scan
            - Additional metadata about the scan
        """
        if not self._client:
            return []
            
        try:
            scan_list = self._client.get_scans()
            return scan_list.saved
        except Exception as e:
            print(f"Error listing scans: {e}")
            return []
    
    def run_scan(self, scan_id: int) -> Dict[str, Any]:
        """Execute a specific saved scan
        
        Args:
            scan_id (int): ID of the scan to run
            
        Returns:
            Dict[str, Any]: Dictionary containing scan results.
            Returns empty dict if client is not initialized or an error occurs.
            
        Note:
            The results dictionary contains:
            - items: List of trade opportunities
            - totalCount: Total number of results
            - pageSize: Number of results per page
            
            See project_codex/option_samurai_scans.md for full response structure.
        """
        if not self._client:
            return {}
            
        try:
            return self._client.execute_scan(scan_id=scan_id, page=0)
        except Exception as e:
            print(f"Error running scan: {e}")
            return {} 