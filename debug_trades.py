import logging
import logging.config
from pathlib import Path
from datetime import datetime
from src.database.db_manager import DatabaseManager
import json
from src.logging_config import setup_logging, get_logger

# Configure test logging
setup_logging('test') # Use centralized test config

logger = get_logger(__name__) # Use helper function

def debug_expired_trades():
    db_manager = DatabaseManager()
    try:
        active_trades = db_manager.get_active_trades()
        logger.info(f"Number of active trades: {len(active_trades)}")
        
        today = datetime.now().date()
        expired_trades = []
        
        for trade in active_trades:
            expiration_date = datetime.strptime(trade['expiration_date'], '%Y-%m-%d').date()
            days_left = (expiration_date - today).days
            
            if days_left < 0:
                expired_trades.append({
                    'trade_id': trade['trade_id'],
                    'symbol': trade['symbol'],
                    'trade_type': trade['trade_type'],
                    'expiration_date': trade['expiration_date'],
                    'days_left': days_left,
                    'status': trade['status']
                })
        
        if expired_trades:
            logger.warning(f"Found {len(expired_trades)} trades with negative days left!")
            for trade in expired_trades:
                logger.warning(json.dumps(trade, indent=2))
        else:
            logger.info("No trades found with negative days left.")

    except Exception as e:
        logger.error(f"Error in debug_expired_trades: {e}", exc_info=True)
    finally:
        db_manager.close()

if __name__ == "__main__":
    debug_expired_trades()