"""
Test script for Option Samurai service integration.
Tests basic functionality of scan listing and execution.

This module provides functionality to:
1. Run predefined option strategy scans
2. Format and save scan results
3. Display human-readable summaries of trade opportunities
"""

import os
import sys
from pathlib import Path
import logging
from typing import Dict, Any
import json
from datetime import datetime
import re

# Add src to Python path
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))

from services.optionsamurai_service import OptionSamuraiService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def safe_filename(name: str) -> str:
    """Convert a string to a safe filename by removing invalid characters.
    
    Args:
        name (str): Original filename or string to convert
        
    Returns:
        str: A safe filename containing only alphanumeric characters and underscores
    """
    # Replace any non-alphanumeric characters with underscore
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', name)
    # Remove multiple consecutive underscores
    safe_name = re.sub(r'_+', '_', safe_name)
    # Remove leading/trailing underscores
    return safe_name.strip('_').lower()

def format_scan_results(results: Dict[str, Any], scan_name: str) -> None:
    """Format and display scan results in a readable way, saving full results to file.
    
    Args:
        results (Dict[str, Any]): Raw scan results from Option Samurai API
        scan_name (str): Name of the scan for logging and file naming
        
    Side Effects:
        - Creates scan_results directory if it doesn't exist
        - Saves full results to a JSON file
        - Logs formatted summary of top 5 trades
    """
    logger.info(f"\n=== {scan_name} Results ===")
    
    if not results:
        logger.info("No results returned")
        return
        
    # Create results directory if it doesn't exist
    results_dir = Path('scan_results')
    results_dir.mkdir(exist_ok=True)
        
    # Save results to file for detailed analysis
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = results_dir / f"{timestamp}_{safe_filename(scan_name)}.json"
    
    try:
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Full results saved to {filename}")
    except Exception as e:
        logger.error(f"Error saving results to file: {e}")
    
    # Display summary of results
    try:
        items = results.get('items', [])
        if not items:
            logger.info("No trades found in results")
            logger.info(f"Available keys in results: {list(results.keys())}")
            return
            
        logger.info(f"Found {len(items)} potential trades")
        
        for item in items[:5]:  # Show top 5 trades
            symbol = item.get('name', 'Unknown')
            max_profit = item.get('max_profit', 0)
            max_loss = item.get('max_loss', 0)
            prob_max_profit = item.get('prob_max_profit', 0)
            prob_max_loss = item.get('prob_max_loss', 0)
            days_to_exp = item.get('days_to_expiration', [0])[0]  # Get first expiration
            strikes = item.get('strike', [])
            
            logger.info(f"\nSymbol: {symbol}")
            logger.info(f"Probability of Max Profit: {prob_max_profit:.1%}")
            logger.info(f"Probability of Max Loss: {prob_max_loss:.1%}")
            logger.info(f"Max Profit: ${max_profit:.2f}")
            logger.info(f"Max Loss: ${max_loss:.2f}")
            logger.info(f"Days to Expiration: {days_to_exp:.1f}")
            if strikes:
                logger.info(f"Strikes: {strikes}")
            if max_loss != 0:
                risk_reward = abs(max_profit/max_loss)
                logger.info(f"Risk/Reward: {risk_reward:.2f}")
                
            # Additional useful information
            volume = item.get('volume', 0)
            avg_volume = item.get('average_volume', 0)
            stock_last = item.get('stock_last', 0)
            if volume and avg_volume and stock_last:
                logger.info(f"Stock Price: ${stock_last:.2f}")
                logger.info(f"Option Volume: {volume:,.0f}")
                logger.info(f"Average Stock Volume: {avg_volume:,.0f}")
                
    except Exception as e:
        logger.error(f"Error formatting results: {e}")
        logger.error("Raw results:")
        logger.error(json.dumps(results, indent=2))

def run_selected_scans():
    """Run our selected strategy scans and process their results.
    
    Executes three predefined scans:
    1. High Probability Iron Condors on Index/ETF (ID: 35269)
    2. Bull Call Spreads (ID: 35867)
    3. Bear Put Spreads (ID: 35797)
    
    Side Effects:
        - Logs scan execution progress and errors
        - Saves scan results to files via format_scan_results()
    """
    service = OptionSamuraiService()
    
    # Our selected scan IDs
    scans_to_run = [
        (35269, "High Probability Iron Condors Index ETF"),
        (35867, "Bull Call Spreads"),
        (35797, "Bear Put Spreads")
    ]
    
    for scan_id, scan_name in scans_to_run:
        logger.info(f"\nRunning scan: {scan_name} (ID: {scan_id})")
        try:
            results = service.run_scan(scan_id)
            format_scan_results(results, scan_name)
        except Exception as e:
            logger.error(f"Error running scan {scan_name}: {e}")
            logger.error("Stack trace:", exc_info=True)

if __name__ == "__main__":
    logger.info("Running selected Option Samurai scans...")
    run_selected_scans() 