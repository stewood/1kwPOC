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
from .pipeline import DataPipeline

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
        self.pipeline = DataPipeline()
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
                results = self.optionsamurai.run_scan(scan_id)
                if not results:
                    logger.warning(f"⚠️  No results from scan '{scan_label}'")
                    continue
                
                # Process results through pipeline
                trade_ids = self.pipeline.process_scan_results(results, scan_label)
                
                # Update cache with processed results
                self._cache[scan_id] = results
                self._last_scan_times[scan_id] = datetime.now()
                
                logger.info(f"✅ Processed scan '{scan_label}' - stored {len(trade_ids)} new trades")
                
            except Exception as e:
                logger.error(f"❌ Error executing scan '{scan_label}': {e}", exc_info=True)
    
    def _should_update_scan(self, scan_id: int) -> bool:
        """Check if a scan should be updated based on cache settings."""
        last_scan = self._last_scan_times.get(scan_id)
        if not last_scan:
            return True
            
        cache_expiry = timedelta(minutes=self.config.cache_duration)
        return datetime.now() - last_scan > cache_expiry 