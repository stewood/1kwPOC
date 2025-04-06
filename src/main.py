"""
Main Application Entry Point

Initializes and coordinates all components of the option scanning system.
Handles startup, shutdown, and signal handling for graceful operation.
"""

import sys
import signal
import logging
from typing import Optional

from .config import Config
from .scanner import ScanManager

logger = logging.getLogger(__name__)

class Application:
    """Main application controller.
    
    Handles initialization of all components and coordinates
    their operation, including graceful shutdown on signals.
    """
    
    def __init__(self):
        """Initialize the application components."""
        self.config = Config()
        self.scanner: Optional[ScanManager] = None
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Set up handlers for system signals."""
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
    
    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        if self.scanner:
            self.scanner.stop()
    
    def start(self):
        """Start the application.
        
        Initializes and starts all components in the correct order.
        Handles errors during startup and ensures clean shutdown.
        """
        try:
            logger.info("Starting application...")
            
            # Initialize scanner
            self.scanner = ScanManager(self.config)
            
            # Log configuration (excluding sensitive data)
            logger.info("Configuration loaded: %s", self.config.to_dict())
            
            # Start scanning
            self.scanner.start()
            
        except Exception as e:
            logger.error(f"Error during startup: {e}", exc_info=True)
            self.shutdown(1)
    
    def shutdown(self, exit_code: int = 0):
        """Shutdown the application gracefully.
        
        Args:
            exit_code (int, optional): System exit code. Defaults to 0.
        """
        logger.info("Shutting down application...")
        
        if self.scanner:
            try:
                self.scanner.stop()
            except Exception as e:
                logger.error(f"Error stopping scanner: {e}", exc_info=True)
        
        sys.exit(exit_code)

def main():
    """Application entry point."""
    app = Application()
    app.start()

if __name__ == "__main__":
    main() 