"""
Option Samurai Service Module

Provides integration with Option Samurai API for scan operations and token management.
This module handles:
- API token management
- Scan listing and execution
- Error handling and logging
"""

import os
import json
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from optionsamurai_api import APIClient
from ..config import Config
from ..logging_config import get_logger

class OptionSamuraiService:
    """Service for interacting with Option Samurai API
    
    This service provides a simplified interface to the Option Samurai API,
    handling token management, scan operations, and error cases.
    
    Attributes:
        _client (Optional[APIClient]): The underlying API client instance
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the service with optional configuration
        
        Args:
            config (Optional[Config]): Configuration object containing API token.
                If not provided, service will initialize but remain inactive.
        """
        self._client: Optional[APIClient] = None
        self._config = config
        
        self.logger = get_logger(__name__)
        self.logger.debug("Initializing OptionSamuraiService...")
        
        # Initialize with token from config if available
        if self._config and self._config.optionsamurai_token:
            self.set_token(self._config.optionsamurai_token)
    
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
            self.logger.info("🔑 Initializing Option Samurai API client...")
            self._client = APIClient(bearer_token=token)
            self.logger.info("✅ API client initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"❌ Error setting token: {e}")
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
            self.logger.error("❌ Cannot list scans: API client not initialized")
            return []
            
        try:
            self.logger.info("📋 Fetching available scans from Option Samurai...")
            scan_list = self._client.get_scans()
            
            # Log scan list details
            predefined_count = len(scan_list.predefined or [])
            saved_count = len(scan_list.saved or [])
            self.logger.info(f"Found {predefined_count} predefined scans and {saved_count} saved scans")
            
            # Combine predefined and saved scans
            all_scans = (scan_list.predefined or []) + (scan_list.saved or [])
            
            # Log scan details
            for scan in all_scans:
                scan_id = getattr(scan, 'id', 'Unknown')
                scan_label = getattr(scan, 'label', 'Unknown')
                self.logger.debug(f"Scan: {scan_label} (ID: {scan_id})")
            
            return all_scans
        except Exception as e:
            self.logger.error(f"❌ Error listing scans: {e}", exc_info=True)
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
            self.logger.error("❌ Cannot run scan: API client not initialized")
            return {}
            
        try:
            # Log scan execution
            self.logger.info(f"🎯 Executing scan {scan_id}...")
            
            # Use the APIClient's execute_scan method directly
            results = self._client.execute_scan(scan_id=str(scan_id), page=0)
            
            # Log scan results summary
            items = results.get('items', [])
            total_count = results.get('totalCount', 0)
            page_size = results.get('pageSize', 0)
            
            self.logger.info(f"✅ Scan {scan_id} completed successfully")
            self.logger.info(f"�� Results summary:")
            self.logger.info(f"   - Total items: {total_count}")
            self.logger.info(f"   - Page size: {page_size}")
            self.logger.info(f"   - Items in response: {len(items)}")
            
            # Log detailed results at debug level
            self.logger.debug("Raw scan results:")
            self.logger.debug(json.dumps(results, indent=2))
            
            return results
        except Exception as e:
            self.logger.error(f"❌ Error running scan {scan_id}: {e}", exc_info=True)
            return {} 