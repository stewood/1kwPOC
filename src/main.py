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
import argparse

from .config import Config
from .scanner import ScanManager
from .database.db_manager import DatabaseManager
from .services.optionsamurai_service import OptionSamuraiService
from .services.price_service import PriceService
from .services.price_tracking import PriceTrackingService
from .pipeline.data_pipeline import DataPipeline
from .reporting import ReportingService

# Configure logging
# Logging is configured in config.py
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler('logs/app.log'),
#         logging.StreamHandler()
#     ]
# )

logger = logging.getLogger(__name__)

class Application:
    """
    Main application class.

    This class is the entry point of the application and is responsible for:
    - Initializing and configuring all application components (Config, DatabaseManager, Scanner, Pipeline, Services).
    - Setting up signal handlers for graceful shutdown.
    - Starting and stopping the main application loop.
    - Generating end-of-run reports.
    """
    
    def __init__(self):
        """Initialize the application components."""
        self.config = Config()
        self.db_manager: Optional[DatabaseManager] = None
        self.scanner: Optional[ScanManager] = None
        self.pipeline: Optional[DataPipeline] = None
        self.price_service: Optional[PriceService] = None
        self.price_tracking: Optional[PriceTrackingService] = None
        self.reporting_service: Optional[ReportingService] = None
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
    
    def _handle_shutdown(self, *args):
        """Handle graceful shutdown."""
        logger.info("🛑 Shutting down...")
        try:
            if self.price_tracking:
                self.price_tracking.stop()
            
            # Generate final report
            if self.reporting_service:
                try:
                    report_path = self.reporting_service.generate_end_of_run_report()
                    logger.info(f"📊 Generated final P&L report: {report_path}")
                except Exception as e:
                    logger.error(f"Failed to generate report: {e}")
            
            sys.exit(0)
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            sys.exit(1)
    
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
            self._test_optionsamurai_connection()
            
            # Initialize scanner and pipeline
            logger.info("🚀 Initializing scanner and pipeline...")
            self.scanner = ScanManager(self.config)
            self.pipeline = DataPipeline(db_manager=self.db_manager)
            self.reporting_service = ReportingService(self.db_manager, self.price_service, self.config)
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

    def _test_optionsamurai_connection(self):
        """Test connection to Option Samurai API."""
        logger.info("🔌 Testing Option Samurai connection...")
        try:
            optionsamurai = OptionSamuraiService(self.config)
            scans = optionsamurai.list_scans()
            logger.info(f"✅ Connected to Option Samurai. Found {len(scans)} available scans.")
            if not scans:
                logger.warning("⚠️ Connected to Option Samurai but no scans found. Please create some scans first.")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Option Samurai: {e}")

def main():
    """Main entry point."""
    
    # --- Argument Parsing --- 
    parser = argparse.ArgumentParser(description="Run the Option Samurai trading helper application.")
    parser.add_argument(
        '--init-db',
        action='store_true',
        help='Initialize the database schema (create tables/indexes if needed) and exit.'
    )
    parser.add_argument(
        '--fetch-scans',
        action='store_true',
        help='Fetch latest results for configured scans from Option Samurai and store them in the database, then exit.'
    )
    parser.add_argument(
        '--update-prices',
        action='store_true',
        help='Update current market prices for options in active trades using Tradier and store them, then exit.'
    )
    parser.add_argument(
        '--generate-report',
        action='store_true',
        help='Generate the end-of-run P&L report based on database data and current prices, then exit.'
    )
    args = parser.parse_args()
    # --- End Argument Parsing --- 
    
    # --- Conditional Execution --- 
    if args.init_db:
        logger.info("--- Database Initialization Mode (--init-db) ---")
        db_manager = None # Ensure db_manager is defined for finally block
        try:
            logger.info("Initializing Config to get DB path...")
            config = Config()
            logger.info(f"Initializing DatabaseManager with path: {config.db_path}")
            db_manager = DatabaseManager(db_path=config.db_path)
            # The initialize_database() call happens within DatabaseManager.__init__ now
            logger.info("✅ Database initialized successfully (tables created/verified)." ) 
        except Exception as e:
             logger.error(f"❌ Error during database initialization: {e}", exc_info=True)
             sys.exit(1)
        finally:
             if db_manager:
                logger.info("Closing database manager...")
                db_manager.close()
        logger.info("--- Database Initialization Complete --- Exiting.")
        sys.exit(0) # Exit after initializing DB

    elif args.fetch_scans:
        logger.info("--- Scan Fetch & Store Mode (--fetch-scans) ---")
        db_manager = None # Ensure defined for finally
        scanner = None # Ensure defined
        try:
            logger.info("Initializing Config...")
            config = Config()
            logger.info(f"Initializing DatabaseManager with path: {config.db_path}")
            db_manager = DatabaseManager(db_path=config.db_path)
            logger.info("Initializing ScanManager...")
            # Pass config and db_manager to ScanManager constructor
            scanner = ScanManager(config=config, db_manager=db_manager) 
            logger.info("Running scan cycle to fetch and store...")
            scanner._run_scan_cycle() # Call the method to fetch/store
            logger.info("✅ Scan fetch and store process completed successfully.")
        except Exception as e:
            logger.error(f"❌ Error during scan fetch and store: {e}", exc_info=True)
            sys.exit(1)
        finally:
            if db_manager:
                logger.info("Closing database manager...")
                db_manager.close()
            # No specific shutdown needed for ScanManager itself in this context
        logger.info("--- Scan Fetch & Store Complete --- Exiting.")
        sys.exit(0) # Exit after fetching scans

    elif args.update_prices:
        logger.info("--- Price Update Mode (--update-prices) ---")
        db_manager = None
        price_service = None
        price_tracking_service = None
        try:
            logger.info("Initializing Config...")
            config = Config()
            
            # Check for Tradier token
            if not config.tradier_token:
                logger.error("❌ TRADIER_TOKEN not found in environment variables. Price updates require this token.")
                sys.exit(1)
            logger.info("✅ Tradier token found.")

            logger.info(f"Initializing DatabaseManager with path: {config.db_path}")
            db_manager = DatabaseManager(db_path=config.db_path)
            
            logger.info("Initializing PriceService...")
            try:
                price_service = PriceService() # Assumes PriceService uses Config internally or needs it passed
                # If PriceService needs config passed: price_service = PriceService(config=config)
                logger.info("✅ PriceService initialized.")
            except ValueError as e:
                 logger.error(f"❌ Failed to initialize PriceService: {e}")
                 sys.exit(1)

            logger.info("Initializing PriceTrackingService...")
            price_tracking_service = PriceTrackingService(
                db_manager=db_manager, 
                price_service=price_service
            )
            logger.info("✅ PriceTrackingService initialized.")

            logger.info("📈 Updating option prices for active trades...")
            price_tracking_service.update_prices() # Call the update method
            logger.info("✅ Price updates completed successfully.")

        except Exception as e:
            logger.error(f"❌ Error during price update: {e}", exc_info=True)
            sys.exit(1)
        finally:
            if db_manager:
                logger.info("Closing database manager...")
                db_manager.close()
            # No specific shutdown needed for PriceService or PriceTrackingService
        logger.info("--- Price Update Complete --- Exiting.")
        sys.exit(0) # Exit after updating prices

    elif args.generate_report:
        logger.info("--- Report Generation Mode (--generate-report) ---")
        db_manager = None
        price_service = None
        reporting_service = None
        try:
            logger.info("Initializing Config...")
            config = Config()
            
            # Check for Tradier token (needed for PriceService dependency)
            if not config.tradier_token:
                logger.error("❌ TRADIER_TOKEN not found. Report generation requires current prices via PriceService.")
                sys.exit(1)
            logger.info("✅ Tradier token found.")

            logger.info(f"Initializing DatabaseManager with path: {config.db_path}")
            db_manager = DatabaseManager(db_path=config.db_path)
            
            logger.info("Initializing PriceService...")
            try:
                price_service = PriceService() 
                logger.info("✅ PriceService initialized.")
            except ValueError as e:
                 logger.error(f"❌ Failed to initialize PriceService: {e}")
                 sys.exit(1)

            logger.info("Initializing ReportingService...")
            reporting_service = ReportingService(
                db_manager=db_manager, 
                price_service=price_service,
                config=config # Pass config as it might be used for report settings
            )
            logger.info("✅ ReportingService initialized.")

            logger.info("📊 Generating end-of-run report...")
            # Assuming generate_end_of_run_report uses a default output dir or one from config
            report_path = reporting_service.generate_end_of_run_report() 
            logger.info(f"✅ Report generated successfully: {report_path}")

        except Exception as e:
            logger.error(f"❌ Error during report generation: {e}", exc_info=True)
            sys.exit(1)
        finally:
            if db_manager:
                logger.info("Closing database manager...")
                db_manager.close()
            # No specific shutdown needed for PriceService or ReportingService
        logger.info("--- Report Generation Complete --- Exiting.")
        sys.exit(0) # Exit after generating report

    else:
        # --- Normal Application Flow --- 
        logger.info("--- Starting Normal Application Run --- ")
        app = Application()
        app.start()
        # The shutdown logic including report generation is now handled by signal handlers
        # or when start() naturally finishes (though currently start() likely runs indefinitely or just one cycle)
        # We might need a more explicit run loop or mechanism if start() is intended to be short-lived
        logger.info("Application start() method finished. Waiting for shutdown signal (Ctrl+C)...")
        # Keep the main thread alive if needed, e.g., if price tracking runs in background threads
        # For now, assume start() runs its course or signal handlers manage exit.
        # signal.pause() # Uncomment if background tasks need the main thread to wait indefinitely


if __name__ == '__main__':
    main() 