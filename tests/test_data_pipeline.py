"""
Test script for data pipeline integration.
Tests the full flow from Option Samurai scan results to database storage.

This module tests:
1. Running option strategy scans
2. Processing results through the data pipeline
3. Storing trades in the database
4. Verifying stored trade data
"""

import os
import sys
from pathlib import Path
import logging
from typing import Dict, Any
import json
from datetime import datetime
import sqlite3
from pprint import pformat

# Add src to Python path
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))

from services.optionsamurai_service import OptionSamuraiService
from pipeline import DataPipeline
from database.db_manager import DatabaseManager
from config import Config
from src.logging_config import setup_logging, get_logger

# Configure test logging
setup_logging('test') # Use centralized test config

logger = get_logger(__name__) # Use helper function

def save_debug_data(data: Dict[str, Any], filename: str) -> None:
    """Save data to a debug file for analysis.
    
    Args:
        data: Data to save
        filename: Name of debug file
    """
    debug_dir = Path('logs/debug')
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    filepath = debug_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}.json"
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        logger.debug(f"Saved debug data to {filepath}")
    except Exception as e:
        logger.error(f"Failed to save debug data: {e}")

def setup_test_database() -> DatabaseManager:
    """Create a test database instance.
    
    Returns:
        DatabaseManager: Configured for testing
    """
    # Use a test-specific database file
    test_db_path = 'data/db/test_trades.db'
    logger.info(f"Setting up test database at: {test_db_path}")
    
    # Delete existing database file if it exists
    if os.path.exists(test_db_path):
        logger.info("Removing existing test database")
        os.remove(test_db_path)
    
    return DatabaseManager(db_path=test_db_path)

def verify_trade_data(db: DatabaseManager, trade_id: int, original_data: Dict[str, Any]) -> bool:
    """Verify that a trade was stored correctly.
    
    Args:
        db: Database manager instance
        trade_id: ID of trade to verify
        original_data: Original scan result data for comparison
        
    Returns:
        bool: True if trade data is valid
    """
    logger.debug(f"\nVerifying trade {trade_id}")
    logger.debug("Original scan data:")
    logger.debug(pformat(original_data))
    
    with db.get_connection() as conn:
        cursor = conn.execute('''
            SELECT * FROM active_trades WHERE trade_id = ?
        ''', (trade_id,))
        trade = cursor.fetchone()
        
        if not trade:
            logger.error(f"Trade {trade_id} not found in database")
            return False
            
        # Convert row to dict for easier access
        trade_dict = dict(trade)
        logger.debug("Stored trade data:")
        logger.debug(pformat(trade_dict))
        
        # Verify required fields
        required_fields = [
            'symbol', 'underlying_price', 'trade_type',
            'entry_date', 'expiration_date', 'net_credit'
        ]
        
        logger.debug("Checking required fields...")
        for field in required_fields:
            if not trade_dict.get(field):
                logger.error(f"Missing required field: {field}")
                return False
            logger.debug(f"✓ {field}: {trade_dict[field]}")
                
        # Verify trade type specific fields
        logger.debug(f"Checking {trade_dict['trade_type']} specific fields...")
        if trade_dict['trade_type'] == 'BULL_PUT':
            if not (trade_dict['short_put'] and trade_dict['long_put']):
                logger.error("Missing put strikes for BULL_PUT spread")
                logger.debug(f"short_put: {trade_dict['short_put']}")
                logger.debug(f"long_put: {trade_dict['long_put']}")
                return False
            logger.debug(f"✓ Put strikes - Short: {trade_dict['short_put']}, Long: {trade_dict['long_put']}")
                
        elif trade_dict['trade_type'] == 'BEAR_CALL':
            if not (trade_dict['short_call'] and trade_dict['long_call']):
                logger.error("Missing call strikes for BEAR_CALL spread")
                logger.debug(f"short_call: {trade_dict['short_call']}")
                logger.debug(f"long_call: {trade_dict['long_call']}")
                return False
            logger.debug(f"✓ Call strikes - Short: {trade_dict['short_call']}, Long: {trade_dict['long_call']}")
                
        elif trade_dict['trade_type'] == 'IRON_CONDOR':
            if not (trade_dict['short_put'] and trade_dict['long_put'] and 
                   trade_dict['short_call'] and trade_dict['long_call']):
                logger.error("Missing strikes for IRON_CONDOR")
                logger.debug(f"short_put: {trade_dict['short_put']}")
                logger.debug(f"long_put: {trade_dict['long_put']}")
                logger.debug(f"short_call: {trade_dict['short_call']}")
                logger.debug(f"long_call: {trade_dict['long_call']}")
                return False
            logger.debug("✓ All IC strikes present")
            logger.debug(f"Puts - Short: {trade_dict['short_put']}, Long: {trade_dict['long_put']}")
            logger.debug(f"Calls - Short: {trade_dict['short_call']}, Long: {trade_dict['long_call']}")
        
        # Compare with original data
        logger.debug("Comparing with original data...")
        symbol_match = trade_dict['symbol'] == original_data.get('name')
        logger.debug(f"Symbol match: {symbol_match} ({trade_dict['symbol']} vs {original_data.get('name')})")
        
        price_match = abs(float(trade_dict['underlying_price']) - float(original_data.get('stock_last', 0))) < 0.01
        logger.debug(f"Price match: {price_match} ({trade_dict['underlying_price']} vs {original_data.get('stock_last')})")
        
        logger.info(f"Trade {trade_id} verification passed")
        return True

def test_pipeline_integration():
    """Test the full pipeline from scan results to database storage."""
    
    logger.info("Starting pipeline integration test")
    logger.debug("Python version: " + sys.version)
    logger.debug("Current working directory: " + os.getcwd())
    
    # Initialize components
    service = OptionSamuraiService()
    db = setup_test_database()
    pipeline = DataPipeline(db_manager=db)
    
    # Our test scans (using existing scan IDs)
    scans_to_test = [
        (35269, "High Probability Iron Condors Index ETF"),
        (35867, "Bull Call Spreads"),
        (35797, "Bear Put Spreads")
    ]
    
    total_trades = 0
    verified_trades = 0
    
    for scan_id, scan_name in scans_to_test:
        logger.info(f"\nTesting scan: {scan_name} (ID: {scan_id})")
        
        try:
            # Get scan results
            logger.debug(f"Fetching results for scan {scan_id}")
            results = service.run_scan(scan_id)
            
            if not results:
                logger.warning(f"No results from scan: {scan_name}")
                continue
            
            # Save raw results for debugging
            save_debug_data(results, f"raw_scan_{scan_id}")
            
            # Log summary of results
            items = results.get('items', [])
            logger.info(f"Received {len(items)} items from scan")
            if items:
                logger.debug("First result keys: " + ", ".join(items[0].keys()))
                
            # Process through pipeline
            logger.debug("Processing results through pipeline...")
            trade_ids = pipeline.process_scan_results(results, scan_name)
            
            logger.info(f"Processed {len(trade_ids)} trades from {scan_name}")
            total_trades += len(trade_ids)
            
            # Verify each trade
            for i, trade_id in enumerate(trade_ids):
                logger.debug(f"\nVerifying trade {i+1} of {len(trade_ids)}")
                if verify_trade_data(db, trade_id, items[i]):
                    verified_trades += 1
                    
        except Exception as e:
            logger.error(f"Error processing {scan_name}: {e}")
            logger.error("Stack trace:", exc_info=True)
    
    # Log summary
    logger.info("\n=== Test Summary ===")
    logger.info(f"Total trades processed: {total_trades}")
    logger.info(f"Successfully verified: {verified_trades}")
    success_rate = f"{(verified_trades/total_trades*100):.1f}%" if total_trades > 0 else "N/A"
    logger.info(f"Success rate: {success_rate}")

if __name__ == "__main__":
    logger.info("Running data pipeline integration test...")
    test_pipeline_integration() 