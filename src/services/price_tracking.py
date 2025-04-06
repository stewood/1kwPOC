"""
Price Tracking Service

Handles periodic updates of option prices for active trades using the Tradier API.
Maintains price history and provides real-time updates for monitoring positions.
"""

import logging
import threading
import time
from datetime import datetime, date
from typing import Dict, List, Optional, Any

from ..config import Config
from ..database.db_manager import DatabaseManager
from ..utils.market_hours import is_market_open, get_next_market_close
from uvatradier import Tradier

logger = logging.getLogger(__name__)

class PriceTrackingService:
    """Service for tracking option prices of active trades."""
    
    def __init__(self, config: Config, db_manager: DatabaseManager):
        """Initialize the price tracking service.
        
        Args:
            config: Application configuration
            db_manager: Database manager instance
        """
        self.config = config
        self.db = db_manager
        self.tradier = Tradier(
            token=config.tradier_token,
            account_id=None,  # Not needed for market data
            sandbox=config.tradier_sandbox
        )
        self._stop_event = threading.Event()
        self._tracking_thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start the price tracking service."""
        if self._tracking_thread and self._tracking_thread.is_alive():
            logger.warning("Price tracking service is already running")
            return
            
        self._stop_event.clear()
        self._tracking_thread = threading.Thread(
            target=self._tracking_loop,
            name="PriceTrackingThread",
            daemon=True
        )
        self._tracking_thread.start()
        logger.info("Price tracking service started")
    
    def stop(self):
        """Stop the price tracking service."""
        if not self._tracking_thread:
            return
            
        logger.info("Stopping price tracking service...")
        self._stop_event.set()
        self._tracking_thread.join(timeout=30)
        if self._tracking_thread.is_alive():
            logger.warning("Price tracking thread did not stop gracefully")
        else:
            logger.info("Price tracking service stopped")
    
    def _tracking_loop(self):
        """Main tracking loop that updates prices periodically."""
        while not self._stop_event.is_set():
            try:
                if not is_market_open():
                    # Sleep until next market open or stop event
                    logger.info("Market is closed. Waiting for next market open...")
                    self._stop_event.wait(300)  # Check every 5 minutes
                    continue
                
                # Get active trades that need price updates
                active_trades = self.db.get_active_trades(status='OPEN')
                if not active_trades:
                    logger.debug("No active trades to track")
                    self._stop_event.wait(60)  # Check every minute
                    continue
                
                self._update_prices(active_trades)
                
                # Check if market is about to close
                next_close = get_next_market_close()
                if next_close and (next_close - datetime.now()).total_seconds() < 300:
                    self._finalize_daily_tracking()
                
                # Wait for next update cycle or stop event
                self._stop_event.wait(self.config.scan_interval)
                
            except Exception as e:
                logger.error(f"Error in price tracking loop: {e}", exc_info=True)
                self._stop_event.wait(self.config.retry_delay)
    
    def _update_prices(self, trades: List[Dict[str, Any]]):
        """Update prices for all options in active trades.
        
        Args:
            trades: List of active trades to update
        """
        today = date.today().isoformat()
        
        for trade in trades:
            try:
                # Get or create today's tracking records
                tracking_records = {}
                option_symbols = self._get_trade_option_symbols(trade)
                
                for symbol in option_symbols:
                    existing = self.db.get_active_price_tracking(trade['trade_id'])
                    if existing and existing['option_symbol'] == symbol:
                        tracking_records[symbol] = existing['tracking_id']
                    else:
                        tracking_id = self.db.create_option_price_tracking(
                            trade['trade_id'],
                            {
                                'option_symbol': symbol,
                                'tracking_date': today
                            }
                        )
                        tracking_records[symbol] = tracking_id
                
                # Get current prices from Tradier
                quotes = self.tradier.get_option_quotes(option_symbols)
                if not quotes:
                    logger.warning(f"No quotes returned for trade {trade['trade_id']}")
                    continue
                
                # Update tracking records
                for quote in quotes:
                    tracking_id = tracking_records.get(quote['symbol'])
                    if not tracking_id:
                        continue
                        
                    self.db.update_option_price(tracking_id, {
                        'bid': quote.get('bid'),
                        'ask': quote.get('ask'),
                        'last': quote.get('last'),
                        'mark': (quote.get('bid', 0) + quote.get('ask', 0)) / 2,
                        'bid_size': quote.get('bidsize'),
                        'ask_size': quote.get('asksize'),
                        'volume': quote.get('volume'),
                        'open_interest': quote.get('open_interest'),
                        'exchange': quote.get('exchange'),
                        
                        # Greeks and IVs if available
                        'delta': quote.get('greeks', {}).get('delta'),
                        'gamma': quote.get('greeks', {}).get('gamma'),
                        'theta': quote.get('greeks', {}).get('theta'),
                        'vega': quote.get('greeks', {}).get('vega'),
                        'rho': quote.get('greeks', {}).get('rho'),
                        'phi': quote.get('greeks', {}).get('phi'),
                        'bid_iv': quote.get('bid_iv'),
                        'mid_iv': quote.get('mid_iv'),
                        'ask_iv': quote.get('ask_iv'),
                        'smv_vol': quote.get('smv_vol'),
                        
                        # Contract details
                        'contract_size': quote.get('contract_size'),
                        'expiration_type': quote.get('expiration_type'),
                        
                        # Market status
                        'is_closing_only': quote.get('closing_only', False),
                        'is_tradeable': quote.get('tradeable', True),
                        'is_market_closed': not is_market_open(),
                        
                        # Update timestamp for Greeks if present
                        'greeks_update_time': (
                            datetime.now().isoformat()
                            if quote.get('greeks')
                            else None
                        )
                    })
                
            except Exception as e:
                logger.error(
                    f"Error updating prices for trade {trade['trade_id']}: {e}",
                    exc_info=True
                )
    
    def _finalize_daily_tracking(self):
        """Mark all today's tracking records as complete at market close."""
        try:
            active_trades = self.db.get_active_trades()
            today = date.today().isoformat()
            
            for trade in active_trades:
                tracking = self.db.get_active_price_tracking(trade['trade_id'])
                if tracking and not tracking['is_complete']:
                    self.db.mark_tracking_complete(tracking['tracking_id'])
            
            logger.info("Finalized daily price tracking records")
            
        except Exception as e:
            logger.error(f"Error finalizing daily tracking: {e}", exc_info=True)
    
    def _get_trade_option_symbols(self, trade: Dict[str, Any]) -> List[str]:
        """Get all option symbols for a trade.
        
        Args:
            trade: Trade dictionary from database
        
        Returns:
            List of OCC option symbols in the trade
        """
        symbols = []
        
        # Add symbols based on trade type
        if trade['trade_type'] in ['BULL_PUT', 'IRON_CONDOR']:
            if trade.get('short_put_symbol'):
                symbols.append(trade['short_put_symbol'])
            if trade.get('long_put_symbol'):
                symbols.append(trade['long_put_symbol'])
                
        if trade['trade_type'] in ['BEAR_CALL', 'IRON_CONDOR']:
            if trade.get('short_call_symbol'):
                symbols.append(trade['short_call_symbol'])
            if trade.get('long_call_symbol'):
                symbols.append(trade['long_call_symbol'])
        
        return symbols 