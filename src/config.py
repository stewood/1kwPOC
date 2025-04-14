"""
Configuration Management Module

Handles loading and managing configuration settings from:
- Environment variables (.env)
- Configuration files
- Command line arguments (future)

Provides centralized access to all application settings.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

from .logging_config import get_logger, setup_logging

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DB_DIR = BASE_DIR / "db"
LOGS_DIR = BASE_DIR / "logs"
SCAN_RESULTS_DIR = BASE_DIR / "scan_results"

# Ensure directories exist
for directory in [DATA_DIR, DB_DIR, LOGS_DIR, SCAN_RESULTS_DIR]:
    directory.mkdir(exist_ok=True)

# Initialize logging
setup_logging()
logger = get_logger(__name__)

class Config:
    """Application configuration management.
    
    Handles loading and providing access to all configuration settings.
    Implements the Singleton pattern to ensure consistent settings across the app.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # Load environment variables
        load_dotenv()
        
        logger.debug("Initializing Config...")
        
        # API Settings
        self.optionsamurai_token = os.getenv("OPTIONSAMURAI_BEARER_TOKEN")
        logger.debug("Option Samurai token found: %s", 'Yes' if self.optionsamurai_token else 'No')
        self.tradier_token = os.getenv("TRADIER_TOKEN")
        self.tradier_sandbox = os.getenv("TRADIER_SANDBOX", "true").lower() == "true"
        
        # Strategy Scan IDs
        self.iron_condor_scan_ids = self._parse_scan_ids("IRON_CONDOR_SCAN_IDS")
        self.bull_call_scan_ids = self._parse_scan_ids("BULL_CALL_SCAN_IDS")
        self.bear_put_scan_ids = self._parse_scan_ids("BEAR_PUT_SCAN_IDS")
        
        # Scanning Settings
        self.scan_interval = int(os.getenv("SCAN_INTERVAL_SECONDS", "300"))  # 5 minutes default
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.retry_delay = int(os.getenv("RETRY_DELAY_SECONDS", "60"))
        
        # Database Settings
        self.db_path = os.getenv("DB_PATH", str(DB_DIR / "trades.db"))
        
        # Scan Settings
        self.cache_duration = int(os.getenv("CACHE_DURATION_MINUTES", "60"))
        self.min_profit_threshold = float(os.getenv("MIN_PROFIT_THRESHOLD", "0.1"))
        self.max_risk_threshold = float(os.getenv("MAX_RISK_THRESHOLD", "0.5"))
        
        logger.info("Configuration initialized successfully")
        self._initialized = True
    
    def _parse_scan_ids(self, env_var: str) -> List[int]:
        """Parse comma-separated scan IDs from environment variable.
        
        Args:
            env_var: Name of the environment variable
            
        Returns:
            List of scan IDs as integers
        """
        scan_ids_str = os.getenv(env_var, "")
        if not scan_ids_str:
            logger.debug("No scan IDs found for %s", env_var)
            return []
            
        try:
            scan_ids = [int(id.strip()) for id in scan_ids_str.split(",") if id.strip()]
            logger.debug("Parsed scan IDs for %s: %s", env_var, scan_ids)
            return scan_ids
        except ValueError as e:
            logger.error("Error parsing scan IDs from %s: %s", env_var, e)
            return []
    
    def get_all_configured_scan_ids(self) -> List[int]:
        """Get all configured scan IDs across all strategies.
        
        Returns:
            List of unique scan IDs as integers
        """
        all_ids = (
            self.iron_condor_scan_ids +
            self.bull_call_scan_ids +
            self.bear_put_scan_ids
        )
        return list(set(all_ids))  # Remove any duplicates
    
    @property
    def database_url(self) -> str:
        """Get the database URL."""
        return f"sqlite:///{self.db_path}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.
        
        Useful for debugging and logging.
        Excludes sensitive information like API tokens.
        """
        return {
            "scan_interval": self.scan_interval,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "db_path": self.db_path,
            "cache_duration": self.cache_duration,
            "min_profit_threshold": self.min_profit_threshold,
            "max_risk_threshold": self.max_risk_threshold,
            "iron_condor_scan_ids": self.iron_condor_scan_ids,
            "bull_call_scan_ids": self.bull_call_scan_ids,
            "bear_put_scan_ids": self.bear_put_scan_ids
        } 