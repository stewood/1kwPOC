"""
Main application entry point.

This module initializes and runs the main application components:
1. Database initialization
2. Option Samurai integration
3. Price tracking
4. Data pipeline
"""

import logging
import signal
import sys
from typing import Optional

from .config import Config
from .scanner import ScanManager
from .database.db_manager import DatabaseManager
from .services.optionsamurai_service import OptionSamuraiService
from .services.price_service import PriceService
from .services.price_tracking import PriceTrackingService
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
    """Main application class."""
    
    def __init__(self):
        """Initialize the application components."""
        self.config = Config()
        self.db_manager: Optional[DatabaseManager] = None
        self.scanner: Optional[ScanManager] = None
        self.pipeline: Optional[DataPipeline] = None
        self.price_service: Optional[PriceService] = None
        self.price_tracking: Optional[PriceTrackingService] = None
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
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
            logger.info("🗄️ Initializing database...")
            self.db_manager = DatabaseManager()
            self.db_manager.initialize_database()
            logger.info("✅ Database initialized successfully")
            
            # Initialize price service if Tradier token available
            if self.config.tradier_token:
                logger.info("🔄 Initializing price service...")
                try:
                    self.price_service = PriceService()
                    logger.info("✅ Price service initialized successfully")
                except ValueError as e:
                    logger.warning(f"⚠️ Price service not initialized: {e}")
            else:
                logger.info("📴 Price service disabled (TRADIER_TOKEN not set)")
            
            # Initialize price tracking
            self.price_tracking = PriceTrackingService(
                db_manager=self.db_manager,
                price_service=self.price_service
            )
            
            # Test Option Samurai connection
            logger.info("🔌 Testing Option Samurai connection...")
            try:
                optionsamurai = OptionSamuraiService()
                scans = optionsamurai.list_scans()
                if scans:
                    logger.info(f"✅ Successfully connected to Option Samurai. Found {len(scans)} available scans:")
                    for scan in scans:
                        logger.info(f"  • {scan.label} (ID: {scan.id})")
                else:
                    logger.warning("⚠️ Connected to Option Samurai but no scans found. Please create some scans first.")
                
                # Initialize scanner and pipeline
                logger.info("🚀 Initializing scanner and pipeline...")
                self.scanner = ScanManager(self.config)
                self.pipeline = DataPipeline(db_manager=self.db_manager)
                logger.info("✅ Components initialized successfully")
                
                # Run a single scan cycle
                logger.info("🔍 Running scan cycle...")
                self.scanner._run_scan_cycle()
                logger.info("✅ Scan cycle completed")
                
                # Update prices for active trades
                if self.price_tracking:
                    logger.info("📈 Updating option prices for active trades...")
                    self.price_tracking.update_prices()
                    logger.info("✅ Price updates completed")
                else:
                    logger.info("⚠️ Price tracking skipped (service not available)")
                
            except Exception as e:
                logger.error(f"❌ Error during scan execution: {e}", exc_info=True)
            finally:
                # Shutdown gracefully
                self.shutdown()
            
        except Exception as e:
            logger.error(f"❌ Error during startup: {e}", exc_info=True)
            self.shutdown()
            sys.exit(1)
    
    def shutdown(self):
        """Shutdown the application gracefully."""
        logger.info("🛑 Shutting down application...")
        
        if self.db_manager:
            logger.info("🗄️ Closing database connections...")
            self.db_manager.close()
            
        logger.info("✅ Shutdown complete")

def main():
    """Main entry point."""
    app = Application()
    app.start()

if __name__ == '__main__':
    main() 