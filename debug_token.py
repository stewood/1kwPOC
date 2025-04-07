import logging
from src.database.db_manager import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_missing_price_data():
    db_manager = DatabaseManager()
    try:
        active_trades = db_manager.get_active_trades()
        logger.info(f"Number of active trades: {len(active_trades)}")
        
        missing_price_data_count = 0
        for trade in active_trades:
            trade_id = trade.get('trade_id')
            trade_type = trade.get('trade_type')
            
            leg_definitions = {
                'BULL_PUT': ['short_put_symbol', 'long_put_symbol'],
                'BEAR_CALL': ['short_call_symbol', 'long_call_symbol'],
                'IRON_CONDOR': ['short_put_symbol', 'long_put_symbol', 'short_call_symbol', 'long_call_symbol']
            }
            
            if trade_type not in leg_definitions:
                logger.warning(f"Unknown trade type: {trade_type} for trade_id: {trade_id}")
                continue
                
            option_symbols = []
            for symbol_field in leg_definitions[trade_type]:
                symbol = trade.get(symbol_field)
                if symbol:
                    option_symbols.append(symbol)
                    
            for option_symbol in option_symbols:
                latest_price_data = db_manager.get_latest_option_price_data(option_symbol)
                if not latest_price_data:
                    logger.warning(f"No price data found for symbol: {option_symbol} in trade_id: {trade_id}")
                    missing_price_data_count += 1
                else:
                    mark_price = latest_price_data.get('mark')
                    last_price = latest_price_data.get('last')
                    bid_price = latest_price_data.get('bid')
                    ask_price = latest_price_data.get('ask')
                    if not any([mark_price, last_price, bid_price, ask_price]):
                        logger.warning(f"No valid price (mark, last, bid, ask) found for symbol: {option_symbol} in trade_id: {trade_id}")
                        missing_price_data_count += 1

        logger.info(f"Total missing price data count: {missing_price_data_count}")

    except Exception as e:
        logger.error(f"Error in debug_missing_price_data: {e}", exc_info=True)
    finally:
        db_manager.close()

if __name__ == "__main__":
    debug_missing_price_data()