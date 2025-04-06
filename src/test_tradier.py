"""
Test script for Tradier market data integration.
Tests basic functionality of the PriceService with sandbox environment.
"""

import os
import logging
from src.services.price_service import PriceService

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for more detailed logs
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_price_service():
    """Test basic PriceService functionality."""
    
    # Set environment variables for testing
    os.environ["TRADIER_TOKEN"] = "U7ehm6FSXJJNW8dQpOyGTDC93sTG"
    os.environ["TRADIER_SANDBOX"] = "true"
    
    try:
        logger.info("Initializing PriceService...")
        service = PriceService()
        
        # Test 1: Get single price
        logger.info("\nTest 1: Getting single price for SPY")
        logger.debug("Calling get_current_price('SPY')...")
        price = service.get_current_price("SPY")
        logger.info(f"SPY Price: ${price}")
        
        # Test 2: Get multiple prices
        logger.info("\nTest 2: Getting multiple prices")
        symbols = ["SPY", "QQQ", "AAPL", "MSFT"]
        logger.debug(f"Calling get_current_prices({symbols})...")
        prices = service.get_current_prices(symbols)
        for symbol, price in prices.items():
            logger.info(f"{symbol}: ${price}")
        
        # Test 3: Get option chain
        logger.info("\nTest 3: Getting option chain for SPY")
        logger.debug("Calling get_option_chain('SPY')...")
        chain = service.get_option_chain("SPY")
        if chain:
            logger.info(f"Expiration: {chain['expiration']}")
            logger.info(f"Number of calls: {len(chain['calls'])}")
            logger.info(f"Number of puts: {len(chain['puts'])}")
            
            # Show sample options
            if chain['calls']:
                logger.info("\nSample calls (first 3):")
                for call in chain['calls'][:3]:
                    logger.info(f"Strike: ${call['strike']}, Bid: ${call['bid']}, Ask: ${call['ask']}")
            
            if chain['puts']:
                logger.info("\nSample puts (first 3):")
                for put in chain['puts'][:3]:
                    logger.info(f"Strike: ${put['strike']}, Bid: ${put['bid']}, Ask: ${put['ask']}")
        
        logger.info("\n✅ All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error during testing: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    test_price_service() 