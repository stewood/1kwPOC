#!/usr/bin/env python3
"""
Test script to run only the reporting service generation.
"""

import os
import sys
import logging
import logging.config
from pathlib import Path
from src.reporting import ReportingService
from src.logging_config import setup_logging, get_logger

# Add src directory to Python path for imports
project_root = Path(__file__).parent
src_path = project_root / 'src'
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# --- Import EXISTING code from your project ---
try:
    from src.config import Config
    from src.database.db_manager import DatabaseManager
    from src.services.price_service import PriceService
except ImportError as e:
    print(f"❌ ERROR: Failed to import necessary project modules: {e}")
    print("Ensure the script is run from the project root and src is in the Python path.")
    print(f"   Project Root: {project_root}")
    print(f"   src Path: {src_path}")
    print(f"   sys.path: {sys.path}")
    sys.exit(1)

# --- Script Logic ---
# Configure test logging
setup_logging('test') # Use centralized test config

logger = get_logger("ReportingTest") # Use helper function, keeping specific name

# Define variables to hold initialized components
db_manager: DatabaseManager | None = None
price_service: PriceService | None = None

try:
    logger.info("--- Starting Reporting Test ---")

    # Initialize necessary components using EXISTING classes
    logger.info("Initializing Config...")
    config = Config()

    # Check for Tradier token, as PriceService needs it
    if not config.tradier_token:
        logger.error("❌ TRADIER_TOKEN not found in environment variables (check .env).")
        logger.error("   PriceService and ReportingService require it.")
        sys.exit(1)
    else:
        logger.info("✅ Tradier token found.")


    logger.info("Initializing DatabaseManager...")
    # Ensure DB directory exists (DatabaseManager doesn't create it)
    db_dir = Path(config.db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Using database at: {config.db_path}")
    db_manager = DatabaseManager(db_path=config.db_path) # Pass specific path from config
    # Optionally initialize tables if needed, assuming reporting reads existing data
    # db_manager.initialize_database() 
    logger.info("✅ DatabaseManager initialized.")

    logger.info("Initializing PriceService...")
    try:
        price_service = PriceService() 
        logger.info("✅ PriceService initialized.")
    except ValueError as e:
        logger.error(f"❌ Failed to initialize PriceService: {e}")
        logger.error("   Ensure TRADIER_TOKEN is valid and Tradier API is accessible.")
        sys.exit(1)


    logger.info("Initializing ReportingService...")
    # Pass the instantiated components and the config object
    reporting_service = ReportingService(
        db_manager=db_manager, 
        price_service=price_service, 
        config=config # Pass the Config object directly
    )
    logger.info("✅ ReportingService initialized.")

    # Call the EXISTING report generation method
    logger.info("⏳ Generating report...")
    try:
        # Create the default 'reports' directory if it doesn't exist
        report_output_dir = project_root / "reports"
        report_output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured report output directory exists: {report_output_dir}")
        
        report_path = reporting_service.generate_end_of_run_report(output_dir=str(report_output_dir)) 
        
        logger.info(f"✅ Report generated successfully: {report_path}")
        # Verify file exists
        if Path(report_path).is_file():
             logger.info("   File confirmed to exist on disk.")
        else:
             logger.warning("   ⚠️ Report path returned, but file not found on disk!")

    except Exception as e: # Catch unexpected errors during generation
        logger.error(f"❌ Unexpected Error during report generation: {e}", exc_info=True)
        sys.exit(1)


except Exception as e: # Catch errors during component initialization
    logger.error(f"❌ An error occurred during setup: {e}", exc_info=True)
    sys.exit(1)

finally:
    # Clean up database connection
    if db_manager:
        logger.info("Closing database connection...")
        try:
            db_manager.close()
            logger.info("✅ Database connection closed.")
        except Exception as e:
            logger.error(f"⚠️ Error closing database connection: {e}")

logger.info("--- Reporting Test Finished ---") 