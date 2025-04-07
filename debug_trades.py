import logging
from src.database.db_manager import DatabaseManager
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_active_trades_data():
    db_manager = DatabaseManager()
    try:
        active_trades = db_manager.get_active_trades()
        logger.info(f"Number of active trades: {len(active_trades)}")
        
        for trade in active_trades:
            logger.info(f"Trade ID: {trade.get('trade_id')}")
            logger.info(json.dumps(trade, indent=2)) # Print full trade details

    except Exception as e:
        logger.error(f"Error in debug_active_trades_data: {e}", exc_info=True)
    finally:
        db_manager.close()

if __name__ == "__main__":
    debug_active_trades_data()