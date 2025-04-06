"""
Scanner Module

Implements the main scanning loop for option trade opportunities.
Handles:
- Periodic scanning using Option Samurai API
- Result caching and deduplication
- Rate limiting and retry logic
- Integration with price verification
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from threading import Event

from .config import Config
from .services.optionsamurai_service import OptionSamuraiService
from .services.price_service import PriceService

logger = logging.getLogger(__name__)

class ScanManager:
    """Manages the scanning process for option trade opportunities.
    
    Coordinates between Option Samurai API and price verification,
    handles caching, and implements retry logic for failures.
    """
    
    def __init__(self, config: Config):
        """Initialize the scan manager.
        
        Args:
            config (Config): Application configuration instance
        """
        self.config = config
        self.optionsamurai = OptionSamuraiService()
        self.price_service = PriceService()
        self.stop_event = Event()
        self._cache: Dict[int, Dict[str, Any]] = {}
        self._last_scan_times: Dict[int, datetime] = {}
        
        # Initialize services
        logger.info("🔄 Initializing Option Samurai service...")
        if not self.optionsamurai._client:
            logger.error("❌ Failed to initialize Option Samurai service. Check your API token.")
            raise RuntimeError("Option Samurai service initialization failed")
        logger.info("✅ Option Samurai service initialized successfully")
        
        logger.info("🔄 Initializing Price service...")
        logger.info("✅ Price service initialized successfully")
    
    def start(self):
        """Start the main scanning loop.
        
        Runs continuously until stop() is called.
        Handles exceptions and implements retry logic.
        """
        logger.info("🚀 Starting scan manager...")
        logger.info("⚙️  Configuration:")
        logger.info(f"   - Scan interval: {self.config.scan_interval} seconds")
        logger.info(f"   - Cache duration: {self.config.cache_duration} minutes")
        logger.info(f"   - Max retries: {self.config.max_retries}")
        
        while not self.stop_event.is_set():
            try:
                self._run_scan_cycle()
                if not self.stop_event.is_set():
                    logger.info(f"💤 Waiting {self.config.scan_interval} seconds until next scan cycle...")
                    self.stop_event.wait(self.config.scan_interval)
            except Exception as e:
                logger.error(f"❌ Error in scan cycle: {e}", exc_info=True)
                if not self.stop_event.is_set():
                    logger.info(f"🔄 Retrying in {self.config.retry_delay} seconds...")
                    self.stop_event.wait(self.config.retry_delay)
    
    def stop(self):
        """Stop the scanning loop gracefully."""
        logger.info("🛑 Stopping scan manager...")
        self.stop_event.set()
    
    def _run_scan_cycle(self):
        """Run a single scan cycle.
        
        Gets available scans from Option Samurai and executes each
        that is due for an update based on cache settings.
        """
        logger.info("📡 Fetching available scans from Option Samurai...")
        scans = self.optionsamurai.list_scans()
        logger.info(f"📋 Found {len(scans)} available scans")
        
        if not scans:
            logger.warning("⚠️  No scans available. Please create some scans in Option Samurai first.")
            return
        
        logger.info("\n🔍 Available scans:")
        for scan in scans:
            logger.info(f"   - {scan.label} (ID: {scan.id})")
        
        for scan in scans:
            scan_id = scan.id
            scan_label = scan.label
            
            # Skip if scan is still cached
            if not self._should_update_scan(scan_id):
                logger.info(f"⏭️  Skipping scan '{scan_label}' - using cached results")
                continue
            
            try:
                logger.info(f"\n🎯 Processing scan: {scan_label}")
                self._execute_scan(scan_id, scan_label)
            except Exception as e:
                logger.error(f"❌ Error executing scan '{scan_label}': {e}", exc_info=True)
    
    def _should_update_scan(self, scan_id: int) -> bool:
        """Check if a scan should be updated based on cache settings."""
        last_scan = self._last_scan_times.get(scan_id)
        if not last_scan:
            return True
            
        cache_expiry = timedelta(minutes=self.config.cache_duration)
        return datetime.now() - last_scan > cache_expiry
    
    def _execute_scan(self, scan_id: int, scan_label: str):
        """Execute a single scan and process its results."""
        logger.info(f"🔄 Executing scan '{scan_label}'...")
        
        retries = 0
        while retries < self.config.max_retries:
            try:
                results = self.optionsamurai.run_scan(scan_id)
                if not results:
                    logger.warning(f"⚠️  No results from scan '{scan_label}'")
                    return
                
                # Process and validate results
                valid_trades = self._process_scan_results(results)
                logger.info(f"✅ Found {len(valid_trades)} valid trades from '{scan_label}'")
                
                if valid_trades:
                    logger.info("\n💡 Valid trade opportunities:")
                    for trade in valid_trades:
                        logger.info(f"   - {trade.get('symbol')}: {trade.get('strategy', 'Unknown strategy')}")
                        logger.info(f"     Max Profit: ${trade.get('maxProfit', 0):.2f}")
                        logger.info(f"     Max Risk: ${trade.get('maxRisk', 0):.2f}")
                        logger.info(f"     Current Price: ${trade.get('underlyingPrice', 0):.2f}")
                
                # Update cache
                self._cache[scan_id] = valid_trades
                self._last_scan_times[scan_id] = datetime.now()
                return
                
            except Exception as e:
                retries += 1
                if retries < self.config.max_retries:
                    logger.warning(f"⚠️  Retry {retries} for '{scan_label}': {e}")
                    time.sleep(self.config.retry_delay)
                else:
                    logger.error(f"❌ Failed to execute '{scan_label}' after {retries} retries")
                    raise
    
    def _process_scan_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process and validate scan results."""
        valid_trades = []
        items = results.get('items', [])
        total_trades = len(items)
        logger.info(f"📊 Processing {total_trades} potential trades...")
        
        for i, trade in enumerate(items, 1):
            symbol = trade.get('symbol', 'Unknown')
            logger.debug(f"Checking trade {i}/{total_trades}: {symbol}")
            
            # Skip if profit is below threshold
            max_profit = trade.get('maxProfit', 0)
            if max_profit < self.config.min_profit_threshold:
                logger.debug(f"   ⚠️  {symbol}: Profit ${max_profit:.2f} below threshold ${self.config.min_profit_threshold:.2f}")
                continue
            
            # Skip if risk is above threshold
            max_risk = trade.get('maxRisk', 1)
            if max_risk > self.config.max_risk_threshold:
                logger.debug(f"   ⚠️  {symbol}: Risk ${max_risk:.2f} above threshold ${self.config.max_risk_threshold:.2f}")
                continue
            
            # Verify current prices
            if not symbol or symbol == 'Unknown':
                continue
            
            try:
                current_price = self.price_service.get_current_price(symbol)
                scan_price = trade.get('underlyingPrice', 0)
                
                if current_price is None:
                    logger.warning(f"   ⚠️  {symbol}: Could not fetch current price")
                    continue
                
                # Skip if price has moved significantly
                if abs(current_price - scan_price) / scan_price > 0.01:  # 1% threshold
                    logger.debug(f"   ⚠️  {symbol}: Price moved {abs(current_price - scan_price) / scan_price:.1%}")
                    continue
                
                logger.debug(f"   ✅ {symbol}: Trade validated")
                valid_trades.append(trade)
                
            except Exception as e:
                logger.warning(f"   ❌ {symbol}: Error verifying price: {e}")
                continue
        
        return valid_trades 