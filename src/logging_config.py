"""
Centralized logging configuration for the application.

This module provides a consistent logging setup across the entire application,
with different log levels for different environments and components.

Logging Levels (from most to least verbose):
    SUPER_DEBUG (5): Intensive troubleshooting
        - Full request/response data
        - Detailed state dumps
        - Cache operations details
        - Performance metrics
        Usage: logger.super_debug("Full API response: %s", response_data)

    DEBUG (10): Detailed debugging information
        - Function entry/exit points
        - Variable values
        - Flow control decisions
        - Cache hits/misses
        Usage: logger.debug("Processing trade with ID: %s", trade_id)

    INFO (20): General operational events
        - Successful operations
        - State changes
        - Configuration updates
        - Cache updates
        Usage: logger.info("Successfully processed %d trades", count)

    WARNING (30): Unexpected but handled situations
        - API rate limit approaches
        - Missing optional data
        - Configuration defaults used
        - Retry attempts
        Usage: logger.warning("Rate limit approaching: %d requests remaining", remaining)

    ERROR (40): Failed operations that need attention
        - API failures
        - Database errors
        - Invalid data
        - Configuration errors
        Usage: logger.error("Failed to process trade: %s", error_message)

    CRITICAL (50): System-level failures
        - Database connection losses
        - Configuration file corruption
        - Unhandled exceptions
        Usage: logger.critical("Database connection lost: %s", error)

Environment-Specific Logging:
    Development:
        - Console: DEBUG and above
        - File: INFO and above
        - Debug file: DEBUG and above
        - Error file: ERROR and above
        - Troubleshoot file: SUPER_DEBUG (when enabled)

    Production:
        - Console: WARNING and above
        - File: INFO and above
        - Debug file: DEBUG and above
        - Error file: ERROR and above
        - Troubleshoot file: SUPER_DEBUG (when enabled)

    Test:
        - Console: INFO and above
        - File: DEBUG and above
        - Debug file: DEBUG and above
        - Error file: ERROR and above
        - Troubleshoot file: SUPER_DEBUG (when enabled)

Usage Examples:
    1. Basic logging:
        from src.logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("Processing started")
        logger.error("Operation failed: %s", error)

    2. Troubleshooting:
        from src.logging_config import get_logger, enable_troubleshoot_logging
        logger = get_logger(__name__)
        enable_troubleshoot_logging("api")  # Enable for API component
        logger.super_debug("Full request data: %s", request_data)
        disable_troubleshoot_logging()  # Disable when done

    3. Component-specific logging:
        logger = get_logger("src.api")  # Get API component logger
        logger.debug("API request initiated")
        logger.info("API response received")

Log File Structure:
    - logs/app.log: Main application log (INFO and above)
    - logs/debug/debug.log: Detailed debug information
    - logs/error.log: Error and critical messages
    - logs/troubleshoot/troubleshoot.log: Intensive troubleshooting data
    - logs/test.log: Test-specific logs (in test environment)

Note: All log files are rotated at 10MB with 5 backup files.
"""

import os
import logging.config
from pathlib import Path
from typing import Dict, Any

# Base paths
BASE_DIR = Path(__file__).parent.parent
LOGS_DIR = BASE_DIR / "logs"
DEBUG_DIR = LOGS_DIR / "debug"
TROUBLESHOOT_DIR = LOGS_DIR / "troubleshoot"

# Ensure log directories exist
LOGS_DIR.mkdir(exist_ok=True)
DEBUG_DIR.mkdir(exist_ok=True)
TROUBLESHOOT_DIR.mkdir(exist_ok=True)

# Custom log level for intensive troubleshooting
SUPER_DEBUG = 5
logging.addLevelName(SUPER_DEBUG, "SUPER_DEBUG")

def super_debug(self, message, *args, **kwargs):
    """
    Log a message with SUPER_DEBUG level.
    
    This method is added to the Logger class to support the custom SUPER_DEBUG level.
    Use this for intensive troubleshooting data that should only be logged when
    explicitly enabled.
    
    Args:
        message: The message to log
        *args: Variable length argument list for message formatting
        **kwargs: Arbitrary keyword arguments for logging
    """
    if self.isEnabledFor(SUPER_DEBUG):
        self._log(SUPER_DEBUG, message, args, **kwargs)

# Add the method to the Logger class
logging.Logger.super_debug = super_debug

def get_logging_config(env: str = "development") -> Dict[str, Any]:
    """
    Get logging configuration based on environment.
    
    This function returns a complete logging configuration dictionary that can be
    used with logging.config.dictConfig(). The configuration includes handlers
    for console, file, debug, error, and troubleshoot logging, with appropriate
    formatters and log levels for each environment.
    
    Args:
        env: Environment name ('development', 'production', 'test')
             Determines the logging levels and handlers to use
        
    Returns:
        Dict containing complete logging configuration
        
    Example:
        config = get_logging_config('development')
        logging.config.dictConfig(config)
    """
    # Base configuration
    config = {
        "version": 1,
        "disable_existing_loggers": False,  # Allow other loggers to exist
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            },
            "detailed": {
                "format": "%(asctime)s [%(levelname)s] %(name)s:%(filename)s:%(lineno)d: %(message)s"
            },
            "troubleshoot": {
                "format": "%(asctime)s [%(levelname)s] %(name)s:%(filename)s:%(lineno)d:%(funcName)s: %(message)s"
            }
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
                "level": "INFO",
                "formatter": "detailed",
                "filename": str(LOGS_DIR / "app.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            },
            "debug_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filename": str(DEBUG_DIR / "debug.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": str(LOGS_DIR / "error.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            },
            "troubleshoot_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "SUPER_DEBUG",
                "formatter": "troubleshoot",
                "filename": str(TROUBLESHOOT_DIR / "troubleshoot.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            }
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": True
            },
            "debug": {  # Debug logger
                "handlers": ["debug_file"],
                "level": "DEBUG",
                "propagate": False
            },
            "error": {  # Error logger
                "handlers": ["error_file"],
                "level": "ERROR",
                "propagate": False
            },
            "troubleshoot": {  # Troubleshoot logger
                "handlers": ["troubleshoot_file"],
                "level": "SUPER_DEBUG",
                "propagate": False
            },
            # Component-specific loggers
            "src.services": {  # Services logger
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False
            },
            "src.pipeline": {  # Pipeline logger
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False
            },
            "src.scanner": {  # Scanner logger
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False
            },
            "src.api": {  # API logger
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False
            }
        }
    }
    
    # Environment-specific adjustments
    if env == "development":
        config["handlers"]["console"]["level"] = "DEBUG"
        config["loggers"][""]["level"] = "DEBUG"
        # Add debug_file handler to the root logger in development
        if "debug_file" not in config["loggers"][""]["handlers"]:
             config["loggers"][""]["handlers"].append("debug_file")
            
        # Set component loggers to DEBUG in development
        for logger_name in ["src.services", "src.pipeline", "src.scanner", "src.api"]:
             if logger_name in config["loggers"]: # Check if logger exists before modifying
                 config["loggers"][logger_name]["level"] = "DEBUG"
                 # Optionally add debug_file handler to components too, or rely on root propagation
                 # If components have propagate=False, adding here is necessary for them to log to debug.log
                 # Let's add it for consistency since propagate is False for components
                 if "debug_file" not in config["loggers"][logger_name]["handlers"]:
                      config["loggers"][logger_name]["handlers"].append("debug_file")
    elif env == "production":
        config["handlers"]["console"]["level"] = "WARNING"
        config["loggers"][""]["level"] = "INFO"
        # Keep component loggers at INFO in production
        for logger in ["src.services", "src.pipeline", "src.scanner", "src.api"]:
            config["loggers"][logger]["level"] = "INFO"
    elif env == "test":
        config["handlers"]["console"]["level"] = "INFO"
        config["loggers"][""]["level"] = "DEBUG"
        config["handlers"]["file"]["filename"] = str(LOGS_DIR / "test.log")
        # Set component loggers to DEBUG in test
        for logger in ["src.services", "src.pipeline", "src.scanner", "src.api"]:
            config["loggers"][logger]["level"] = "DEBUG"
    
    return config

def setup_logging(env: str = None) -> None:
    """
    Set up logging configuration for the application.
    
    This function initializes the logging system with the appropriate configuration
    for the specified environment. If no environment is specified, it uses the
    LOG_ENV environment variable or defaults to 'development'.
    
    Args:
        env: Environment name ('development', 'production', 'test')
             If None, uses LOG_ENV environment variable or defaults to 'development'
    
    Example:
        setup_logging('production')  # Set up production logging
        setup_logging()  # Use environment variable or default
    """
    if env is None:
        env = os.getenv("LOG_ENV", "development")
    
    config = get_logging_config(env)
    logging.config.dictConfig(config)
    
    # Log the setup
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured for environment: {env}")
    logger.debug("Debug logging enabled")

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    This function returns a configured logger instance that can be used for
    logging messages. The logger will use the configuration set up by
    setup_logging().
    
    Args:
        name: Logger name (typically __name__)
             This should be the module name for component-specific logging
        
    Returns:
        Configured logger instance
        
    Example:
        logger = get_logger(__name__)
        logger.info("Processing started")
    """
    return logging.getLogger(name)

def enable_troubleshoot_logging(component: str = None) -> None:
    """
    Enable SUPER_DEBUG level logging for troubleshooting.
    
    This function enables intensive troubleshooting logging for either a specific
    component or all components. When enabled, SUPER_DEBUG level messages will
    be logged to the troubleshoot log file.
    
    Args:
        component: Specific component to enable troubleshooting for.
                  If None, enables for all components.
                  Valid values: 'services', 'pipeline', 'scanner', 'api'
    
    Example:
        enable_troubleshoot_logging('api')  # Enable for API component
        enable_troubleshoot_logging()  # Enable for all components
    """
    if component:
        logger = logging.getLogger(f"src.{component}")
    else:
        logger = logging.getLogger("troubleshoot")
    
    logger.setLevel(SUPER_DEBUG)
    logger.super_debug("Troubleshoot logging enabled")

def disable_troubleshoot_logging(component: str = None) -> None:
    """
    Disable SUPER_DEBUG level logging.
    
    This function disables intensive troubleshooting logging for either a specific
    component or all components. After calling this function, SUPER_DEBUG level
    messages will no longer be logged.
    
    Args:
        component: Specific component to disable troubleshooting for.
                  If None, disables for all components.
                  Valid values: 'services', 'pipeline', 'scanner', 'api'
    
    Example:
        disable_troubleshoot_logging('api')  # Disable for API component
        disable_troubleshoot_logging()  # Disable for all components
    """
    if component:
        logger = logging.getLogger(f"src.{component}")
        logger.setLevel(logging.INFO)
    else:
        logger = logging.getLogger("troubleshoot")
        logger.setLevel(logging.INFO) 