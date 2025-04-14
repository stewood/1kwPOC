"""
Price tracking service for monitoring option prices.

This service handles:
- Fetching current option prices from Tradier
- Storing price history in the database
- Managing daily price records
"""

import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
from threading import Lock
import time

from ..database.db_manager import DatabaseManager
from ..services.price_service import PriceService
from ..config import Config
from ..logging_config import get_logger

# Initialize logger using the helper function
logger = get_logger(__name__)

class PriceTrackingService:
    """Service for tracking option prices for active trades."""
    
    def __init__(self, db_manager: DatabaseManager, price_service: Optional[PriceService] = None, max_workers: int = 5):
        """
        Initialize the price tracking service.
        
        Args:
            db_manager: Database manager instance
            price_service: Optional price service instance. If None, price tracking is disabled.
            max_workers: Maximum number of worker threads for API calls
        """
        self.db = db_manager
        self.price_service = price_service
        self.max_workers = max_workers
        self.stats_lock = Lock()
        
    def update_prices(self) -> None:
        """Update prices for all active trades.
        
        This will:
        1. Get all active trades
        2. Process trades in parallel using a thread pool
        3. For each trade's options:
           - Check if we have today's record
           - If no record or record isn't complete:
             * Fetch current prices
             * Store/update in database
             * Mark complete if market is closed
        """
        if not self.price_service:
            logger.info("📴 Price tracking disabled (no price service available)")
            return
            
        try:
            # Get active trades
            active_trades = self.db.get_active_trades()
            if not active_trades:
                logger.info("ℹ️ No active trades to track")
                return
                
            logger.info(f"🔄 Updating prices for {len(active_trades)} active trades using {self.max_workers} workers")
            
            # Initialize stats
            stats = {
                'trades_processed': 0,
                'options_checked': 0,
                'records_created': 0,
                'records_updated': 0,
                'records_completed': 0,
                'errors': 0,
                'total_api_time': 0,
                'max_api_time': 0
            }
            
            # Process trades in parallel
            start_time = time.time()
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all trades for processing
                future_to_trade = {
                    executor.submit(self._process_trade_options, trade, stats): trade
                    for trade in active_trades
                }
                
                # Process completed trades as they finish
                for future in as_completed(future_to_trade):
                    trade = future_to_trade[future]
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"❌ Error processing trade #{trade.get('trade_id', 'Unknown')}: {e}")
                        with self.stats_lock:
                            stats['errors'] += 1
            
            # Calculate timing stats
            total_time = time.time() - start_time
            avg_time_per_trade = total_time / len(active_trades) if active_trades else 0
            
            # Log summary
            logger.info("\n📊 Price tracking summary:")
            logger.info(f"  • Total time: {total_time:.2f}s")
            logger.info(f"  • Average time per trade: {avg_time_per_trade:.2f}s")
            logger.info(f"  • Trades processed: {stats['trades_processed']}")
            logger.info(f"  • Options checked: {stats['options_checked']}")
            logger.info(f"  • Records created: {stats['records_created']}")
            logger.info(f"  • Records updated: {stats['records_updated']}")
            logger.info(f"  • Records completed: {stats['records_completed']}")
            logger.info(f"  • Total API time: {stats['total_api_time']:.2f}s")
            logger.info(f"  • Max API time: {stats['max_api_time']:.2f}s")
            logger.info(f"  • Errors: {stats['errors']}")
                
        except Exception as e:
            logger.error(f"❌ Error updating prices: {e}", exc_info=True)
            
    def _process_trade_options(self, trade: Dict[str, Any], stats: Dict[str, int]) -> None:
        """Process all options for a single trade concurrently.
        
        Args:
            trade: Trade record from database
            stats: Statistics dictionary to update
        """
        try:
            trade_id = trade['trade_id']
            symbol = trade.get('symbol', 'Unknown')
            trade_type = trade.get('trade_type', 'Unknown')
            
            logger.info(f"🔄 Processing trade #{trade_id}: {symbol} {trade_type}")
            
            # Get option symbols
            option_symbols = self._get_trade_option_symbols(trade)
            if not option_symbols:
                logger.warning(f"⚠️ No option symbols found for trade #{trade_id}")
                return
                
            logger.info(f"  • Found {len(option_symbols)} option legs to process")
            
            # Process each option
            with ThreadPoolExecutor(max_workers=len(option_symbols)) as executor:
                # Submit all options for processing
                futures = [
                    executor.submit(self._process_single_option, trade_id, symbol, stats)
                    for symbol in option_symbols
                ]
                
                # Wait for all options to complete
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"❌ Error processing option for trade #{trade_id}: {e}")
                        with self.stats_lock:
                            stats['errors'] += 1
            
            # Update trades processed count
            with self.stats_lock:
                stats['trades_processed'] += 1
                
        except Exception as e:
            logger.error(f"❌ Error processing trade options for #{trade.get('trade_id', 'Unknown')}: {e}")
            with self.stats_lock:
                stats['errors'] += 1
                
    def _process_single_option(self, trade_id: int, symbol: str, stats: Dict[str, int]) -> None:
        """Process a single option contract.
        
        Args:
            trade_id: ID of the trade
            symbol: Option symbol to process
            stats: Statistics dictionary to update
        """
        try:
            logger.info(f"\n📊 Processing option leg: {symbol}")
            
            # Check if we already have a complete record for today
            existing = self.db.get_active_price_tracking(trade_id)
            if existing and existing['is_complete']:
                logger.info(f"  ✅ Already have complete price record for today")
                return
            
            # Log the API call attempt
            logger.info(f"  🌐 Fetching option data from Tradier...")
            start_time = time.time()
            
            # Get current option data
            option_data = self.price_service.get_option_data(symbol)
            
            # Update timing stats
            api_time = time.time() - start_time
            with self.stats_lock:
                stats['total_api_time'] += api_time
                stats['max_api_time'] = max(stats['max_api_time'], api_time)
                stats['options_checked'] += 1
            
            logger.info(f"  ⏱️ API call took {api_time:.2f} seconds")
            
            if not option_data:
                logger.warning(f"  ❌ No data returned from API for {symbol}")
                logger.warning(f"  • This could be due to:")
                logger.warning(f"    - Symbol not found")
                logger.warning(f"    - API error")
                logger.warning(f"    - Invalid option format")
                return
            
            # Log detailed option data
            logger.info(f"  📈 Option Data Details:")
            logger.info(f"    • Bid: {option_data.get('bid', 'N/A')}")
            logger.info(f"    • Ask: {option_data.get('ask', 'N/A')}")
            logger.info(f"    • Last: {option_data.get('last', 'N/A')}")
            logger.info(f"    • Volume: {option_data.get('volume', 'N/A')}")
            logger.info(f"    • Open Interest: {option_data.get('open_interest', 'N/A')}")
            
            # Log market status
            is_closed = option_data.get('is_market_closed', False)
            market_status = "CLOSED" if is_closed else "OPEN"
            logger.info(f"    • Market Status: {market_status}")
            
            # Prepare tracking record
            tracking_data = {
                'option_symbol': symbol,
                'tracking_date': date.today().isoformat(),
                **option_data
            }
            
            # Create/update record
            if existing:
                logger.info(f"  📝 Updating existing price record")
                self.db.update_option_price(existing['tracking_id'], tracking_data)
                with self.stats_lock:
                    stats['records_updated'] += 1
            else:
                logger.info(f"  ✨ Creating new price record")
                self.db.create_option_price_tracking(trade_id, tracking_data)
                with self.stats_lock:
                    stats['records_created'] += 1
                
            # If market is closed, mark record complete
            if option_data.get('is_market_closed', False):
                if existing:
                    logger.info(f"  🔒 Marking record as complete (market closed)")
                    self.db.mark_tracking_complete(existing['tracking_id'])
                    with self.stats_lock:
                        stats['records_completed'] += 1
            
            logger.info(f"  ✅ Finished processing {symbol}\n")
            
        except Exception as e:
            logger.error(f"❌ Error processing option {symbol}: {e}")
            with self.stats_lock:
                stats['errors'] += 1
            
    def _get_trade_option_symbols(self, trade: Dict[str, Any]) -> List[str]:
        """Get all option symbols for a trade.
        
        Args:
            trade: Trade record from database
            
        Returns:
            List of option symbols
        """
        symbols = []
        
        # Get symbols directly from trade record if available
        # This is more reliable than trying to construct them
        if trade.get('short_call_symbol'):
            symbols.append(trade['short_call_symbol'])
        if trade.get('long_call_symbol'):
            symbols.append(trade['long_call_symbol'])
        if trade.get('short_put_symbol'):
            symbols.append(trade['short_put_symbol'])
        if trade.get('long_put_symbol'):
            symbols.append(trade['long_put_symbol'])
            
        return symbols 