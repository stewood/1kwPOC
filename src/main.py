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
from .database.db_manager import DatabaseManager
from .services.optionsamurai_service import OptionSamuraiService
from .pipeline.data_pipeline import DataPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class Application:
    """Main application controller.
    
    Handles initialization of all components and coordinates
    their operation, including graceful shutdown on signals.
    """
    
    def __init__(self):
        """Initialize the application components."""
        self.config = Config()
        self.db_manager: Optional[DatabaseManager] = None
        self.scanner: Optional[ScanManager] = None
        self.pipeline: Optional[DataPipeline] = None
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Set up handlers for system signals."""
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
    
    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info("Received shutdown signal")
        self.shutdown()
        sys.exit(0)
    
    def start(self):
        """Start the application.
        
        Initializes components and runs a single scan cycle.
        """
        try:
            # Initialize database
            logger.info("Initializing database...")
            self.db_manager = DatabaseManager()
            self.db_manager.initialize_database()
            logger.info("Database initialized successfully")
            
            # Test Option Samurai connection
            logger.info("Testing Option Samurai connection...")
            try:
                optionsamurai = OptionSamuraiService()
                scans = optionsamurai.list_scans()
                if scans:
                    logger.info(f"Successfully connected to Option Samurai. Found {len(scans)} available scans:")
                    for scan in scans:
                        logger.info(f"  - {scan.label} (ID: {scan.id})")
                else:
                    logger.warning("Connected to Option Samurai but no scans found. Please create some scans first.")
                
                # Initialize scanner and pipeline
                logger.info("Initializing scanner and pipeline...")
                self.scanner = ScanManager(self.config)
                self.pipeline = DataPipeline(db_manager=self.db_manager)
                logger.info("Components initialized successfully")
                
                # Run a single scan cycle
                logger.info("Running scan cycle...")
                self.scanner._run_scan_cycle()
                logger.info("Scan cycle completed")
                
            except Exception as e:
                logger.error(f"Error during scan execution: {e}", exc_info=True)
            finally:
                # Shutdown gracefully
                self.shutdown()
            
        except Exception as e:
            logger.error(f"Error during startup: {e}", exc_info=True)
            self.shutdown()
            sys.exit(1)
    
    def shutdown(self):
        """Shutdown the application gracefully."""
        logger.info("Shutting down application...")
        
        if self.db_manager:
            logger.info("Closing database connections...")
            self.db_manager.close()
            
        logger.info("Shutdown complete")

def main():
    """Main entry point."""
    app = Application()
    app.start()

if __name__ == "__main__":
    main() 