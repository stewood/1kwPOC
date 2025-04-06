"""
Configuration Management Module

Handles loading and managing configuration settings from:
- Environment variables (.env)
- Configuration files
- Command line arguments (future)

Provides centralized access to all application settings.
"""

import os
import logging.config
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DB_DIR = BASE_DIR / "db"
LOGS_DIR = BASE_DIR / "logs"
SCAN_RESULTS_DIR = BASE_DIR / "scan_results"

# Ensure directories exist
for directory in [DATA_DIR, DB_DIR, LOGS_DIR, SCAN_RESULTS_DIR]:
    directory.mkdir(exist_ok=True)

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
        
        # API Settings
        self.optionsamurai_token = os.getenv("OPTIONSAMURAI_BEARER_TOKEN")
        self.tradier_token = os.getenv("TRADIER_TOKEN")
        self.tradier_sandbox = os.getenv("TRADIER_SANDBOX", "true").lower() == "true"
        self.scan_interval = int(os.getenv("SCAN_INTERVAL_SECONDS", "300"))  # 5 minutes default
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.retry_delay = int(os.getenv("RETRY_DELAY_SECONDS", "60"))
        
        # Database Settings
        self.db_path = os.getenv("DB_PATH", str(DB_DIR / "trades.db"))
        
        # Scan Settings
        self.cache_duration = int(os.getenv("CACHE_DURATION_MINUTES", "60"))
        self.min_profit_threshold = float(os.getenv("MIN_PROFIT_THRESHOLD", "0.1"))
        self.max_risk_threshold = float(os.getenv("MAX_RISK_THRESHOLD", "0.5"))
        
        # Logging Configuration
        self._setup_logging()
        
        self._initialized = True
    
    def _setup_logging(self):
        """Configure logging for the application."""
        logging_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "INFO",
                    "formatter": "standard",
                    "stream": "ext://sys.stdout"
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "DEBUG",
                    "formatter": "standard",
                    "filename": str(LOGS_DIR / "app.log"),
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 5
                }
            },
            "loggers": {
                "": {  # Root logger
                    "handlers": ["console", "file"],
                    "level": os.getenv("LOG_LEVEL", "INFO"),
                    "propagate": True
                }
            }
        }
        
        logging.config.dictConfig(logging_config)
    
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
            "max_risk_threshold": self.max_risk_threshold
        } 