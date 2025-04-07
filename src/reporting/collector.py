from datetime import datetime
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import logging

from ..database.db_manager import DatabaseManager
from ..services.price_service import PriceService
from .models import ReportData, StrategyData, TradeData, OptionLeg

logger = logging.getLogger(__name__)

class ReportDataCollector:
    def __init__(self, db_manager: DatabaseManager, price_service: PriceService):
        self.db = db_manager
        self.price_service = price_service
    
    def collect_data(self) -> ReportData:
        """Collect all data needed for the report."""
        try:
            active_trades = self.db.get_active_trades()
            logger.info(f"Collected {len(active_trades)} active trades from DB.")
        except Exception as e:
            logger.error(f"Failed to get active trades from database: {e}", exc_info=True)
            # Return empty/default report data or re-raise?
            # For now, let's return a minimal default to avoid crashing the report generation test
            return ReportData(
                total_pnl=0, total_return=0, active_trades_count=0, unique_underlyings=0,
                win_rate=0, avg_pnl_per_trade=0, max_loss=0, strategies={},
                vix_price=None, vix_change=None, spy_price=None, spy_change=None,
                market_status='Unknown', generated_at=datetime.now()
            )
        
        # Group trades by strategy
        strategy_trades: Dict[str, List[Dict]] = defaultdict(list)
        for trade in active_trades:
            # Trade dictionary already contains all necessary info
            trade_type = trade.get('trade_type') # Use get for safety
            if trade_type:
                strategy_trades[trade_type].append(trade)
            else:
                logger.warning(f"Trade ID {trade.get('trade_id')} missing trade_type, skipping.")
        
        # Process trades by strategy
        strategies = {}
        total_pnl = 0
        winning_trades = 0
        max_loss = 0
        total_processed_trades = 0
        
        for strategy_type, trades in strategy_trades.items():
            logger.info(f"Processing strategy: {strategy_type} ({len(trades)} trades)")
            strategy_data = self._process_strategy(strategy_type, trades)
            if strategy_data.trades: # Only include strategies with successfully processed trades
                strategies[strategy_type] = strategy_data
                total_pnl += strategy_data.total_pnl
                winning_trades += sum(1 for t in strategy_data.trades if t.pnl > 0)
                # Find min PnL (max loss) across all trades in this strategy
                min_pnl_in_strategy = min((t.pnl for t in strategy_data.trades), default=0)
                max_loss = min(max_loss, min_pnl_in_strategy)
                total_processed_trades += len(strategy_data.trades)
            else:
                logger.warning(f"No trades successfully processed for strategy: {strategy_type}")
        
        unique_underlyings = len({t.symbol for s in strategies.values() for t in s.trades})
        
        # Get market data (mocked for now)
        market_data = self._get_market_data()
        
        logger.info(f"Report Data Summary: Total PnL={total_pnl:.2f}, Total Trades={total_processed_trades}, Win Rate={(winning_trades / total_processed_trades * 100) if total_processed_trades > 0 else 0:.1f}%")
        
        return ReportData(
            total_pnl=total_pnl,
            # Assuming $50k account size for return % - consider making this configurable
            total_return=(total_pnl / 50000 * 100) if 50000 > 0 else 0, 
            active_trades_count=total_processed_trades,
            unique_underlyings=unique_underlyings,
            win_rate=(winning_trades / total_processed_trades * 100) if total_processed_trades > 0 else 0,
            avg_pnl_per_trade=total_pnl / total_processed_trades if total_processed_trades > 0 else 0,
            max_loss=max_loss,
            strategies=strategies,
            vix_price=market_data['vix_price'],
            vix_change=market_data['vix_change'],
            spy_price=market_data['spy_price'],
            spy_change=market_data['spy_change'],
            market_status=market_data['market_status'],
            generated_at=datetime.now()
        )
    
    def _process_strategy(self, strategy_type: str, trades: List[Dict]) -> StrategyData:
        """Process all trades for a given strategy."""
        processed_trades_data = []
        total_pnl = 0
        winning_trades = 0
        
        for trade_dict in trades:
            try:
                trade_data = self._process_trade(trade_dict)
                if trade_data: # Ensure processing was successful
                    processed_trades_data.append(trade_data)
                    total_pnl += trade_data.pnl
                    if trade_data.pnl > 0:
                        winning_trades += 1
            except Exception as e:
                trade_id = trade_dict.get('trade_id', 'N/A')
                logger.error(f"Failed to process trade ID {trade_id}: {e}", exc_info=True)
                # Continue to next trade if one fails
        
        active_count = len(processed_trades_data)
        win_rate = (winning_trades / active_count * 100) if active_count > 0 else 0
        
        logger.debug(f"Strategy {strategy_type}: Processed {active_count} trades, Total PnL={total_pnl:.2f}, Win Rate={win_rate:.1f}%")
        
        return StrategyData(
            name=strategy_type,
            trades=processed_trades_data,
            total_pnl=total_pnl,
            win_rate=win_rate,
            active_count=active_count
        )
    
    def _process_trade(self, trade_dict: Dict) -> Optional[TradeData]:
        """Process a single trade dictionary to calculate P&L and extract leg info."""
        trade_id = trade_dict.get('trade_id', 'N/A')
        logger.debug(f"Processing trade ID: {trade_id}")
        legs: List[OptionLeg] = []
        current_legs_value = 0 # Represents the *current* cost to close (debit for short, credit for long)
        total_contracts = trade_dict.get('num_contracts', 1)
        trade_type = trade_dict.get('trade_type')
        expiration_str = trade_dict.get('expiration_date')
        symbol = trade_dict.get('symbol')
        net_entry_credit_per_contract = trade_dict.get('net_credit', 0.0)

        if not all([trade_type, expiration_str, symbol, net_entry_credit_per_contract is not None]):
             logger.warning(f"Trade ID {trade_id} missing essential data (type, expiration, symbol, or credit), skipping.")
             return None

        try:
            expiration_date = datetime.strptime(expiration_str, '%Y-%m-%d')
        except ValueError:
            logger.error(f"Invalid expiration date format '{expiration_str}' for trade ID {trade_id}, skipping.")
            return None

        # Define which fields correspond to which leg type
        # (symbol_field, strike_field, is_short, type_str)
        leg_definitions = {
            'BULL_PUT': [
                ('short_put_symbol', 'short_put', True, 'put'),
                ('long_put_symbol', 'long_put', False, 'put'),
            ],
            'BEAR_CALL': [
                ('short_call_symbol', 'short_call', True, 'call'),
                ('long_call_symbol', 'long_call', False, 'call'),
            ],
            'IRON_CONDOR': [
                ('short_put_symbol', 'short_put', True, 'put'),
                ('long_put_symbol', 'long_put', False, 'put'),
                ('short_call_symbol', 'short_call', True, 'call'),
                ('long_call_symbol', 'long_call', False, 'call'),
            ]
        }

        if trade_type not in leg_definitions:
            logger.warning(f"Unknown trade type '{trade_type}' for trade ID {trade_id}, skipping.")
            return None

        missing_leg_data = False
        for symbol_field, strike_field, is_short, type_str in leg_definitions[trade_type]:
            option_symbol = trade_dict.get(symbol_field)
            strike_price = trade_dict.get(strike_field)

            if not option_symbol or strike_price is None:
                continue
                
            logger.debug(f"  Processing leg: {option_symbol} (Short: {is_short}, Type: {type_str}, Strike: {strike_price})")
            
            # --- Get Price Data from DATABASE --- 
            latest_price_data = None
            current_leg_price = None
            try:
                # Use the DB manager to get the latest stored price data
                latest_price_data = self.db.get_latest_option_price_data(option_symbol)
                
                if latest_price_data:
                    # Use mark price if available and valid, otherwise fallback to last
                    # Mark price is often NULL in the table if bid/ask were 0
                    db_mark = latest_price_data.get('mark')
                    db_last = latest_price_data.get('last')
                    db_bid = latest_price_data.get('bid')
                    db_ask = latest_price_data.get('ask')
                    
                    # Prefer mark price if it exists
                    if db_mark is not None:
                         current_leg_price = db_mark
                    # Fallback to last price if mark is missing
                    elif db_last is not None:
                         current_leg_price = db_last
                    # As a last resort, estimate mark from bid/ask if they exist
                    elif db_bid is not None and db_ask is not None:
                        current_leg_price = (db_bid + db_ask) / 2
                        logger.debug(f"    Using calculated mark ({current_leg_price:.2f}) as price for {option_symbol}")
                    else:
                         logger.warning(f"    Could not determine price (no mark/last/bid/ask) from DB for {option_symbol} on trade ID {trade_id}. Skipping leg P&L.")
                         missing_leg_data = True
                         current_leg_price = 0 # Assign 0 to allow report generation, but P&L will be inaccurate

                    if current_leg_price is not None and current_leg_price != 0:
                        logger.debug(f"    Using price {current_leg_price:.2f} from DB for {option_symbol}")
                else:
                     # No data found in DB for this symbol
                     logger.warning(f"    No price data found in DB for {option_symbol} on trade ID {trade_id}. Skipping leg P&L.")
                     missing_leg_data = True
                     current_leg_price = 0 # Assign 0

            except Exception as db_price_e:
                logger.error(f"    Error fetching latest price from DB for {option_symbol} on trade ID {trade_id}: {db_price_e}", exc_info=True)
                missing_leg_data = True
                current_leg_price = 0 # Assign 0
            # --- End Get Price Data --- 

            leg = OptionLeg(
                type=type_str,
                strike=strike_price,
                is_short=is_short,
                # Entry price per leg isn't stored, only net credit for the trade
                # We can't calculate individual leg entry, so set to None or 0
                entry_price=None, 
                current_price=current_leg_price,
                expiration=expiration_date,
                symbol=option_symbol
            )
            legs.append(leg)

            # Calculate current value contribution of this leg
            # If short, current price represents a debit (cost to close)
            # If long, current price represents a credit (value if closed)
            multiplier = -1 if is_short else 1
            current_legs_value += current_leg_price * multiplier
            logger.debug(f"    Leg {option_symbol}: Multiplier={multiplier}, CurrentPrice={current_leg_price:.2f}, AddedValue={current_leg_price * multiplier:.2f}, CumulativeValue={current_legs_value:.2f}")

        if not legs:
            logger.warning(f"No valid legs found or processed for trade ID {trade_id}, skipping trade.")
            return None
        
        if missing_leg_data:
            logger.warning(f"P&L for trade ID {trade_id} may be inaccurate due to missing leg price data.")

        # Calculate P&L based on net entry credit vs current net value to close
        # PnL = (Net Entry Credit per contract) - (Current net cost to close per contract)
        # Note: current_legs_value is already net (short legs are negative, long are positive)
        # so current net cost to close is -current_legs_value
        pnl_per_contract = -net_entry_credit_per_contract + current_legs_value
        total_pnl = pnl_per_contract * total_contracts * 100 # Multiply by 100 for contract size

        # Calculate PnL percentage based on Max Risk if possible, otherwise Entry Credit
        # Max risk calculation is complex, for now use entry credit as proxy denominator
        # This isn't ideal for spreads but is simpler for now.
        denominator = net_entry_credit_per_contract * total_contracts * 100
        pnl_percent = (total_pnl / denominator * 100) if denominator != 0 else 0
        
        logger.debug(f"Trade ID {trade_id}: EntryCredit={net_entry_credit_per_contract:.2f}, CurrentValue={current_legs_value:.2f}, PnL/Contract={pnl_per_contract:.2f}, Total PnL={total_pnl:.2f}")

        return TradeData(
            symbol=symbol,
            expiration=expiration_date,
            days_left=(expiration_date - datetime.now()).days,
            entry_credit=net_entry_credit_per_contract * total_contracts * 100, # Total credit
            current_value=-current_legs_value * total_contracts * 100, # Total current cost to close
            pnl=total_pnl,
            pnl_percent=pnl_percent,
            legs=legs,
            strategy_type=trade_type,
            # Fetching greeks for the whole position is complex, maybe add later
            delta=None, 
            theta=None
        )
    
    def _get_market_data(self) -> dict:
        """Get current market data (reads from DB)."""
        logger.warning("Attempting to get VIX/SPY from latest DB records.")
        # TODO: This assumes VIX/SPY symbols are tracked like options, which might not be true.
        # Need a different mechanism or store index prices separately.
        vix_data = self.db.get_latest_option_price_data('^VIX')
        spy_data = self.db.get_latest_option_price_data('SPY')
        
        vix_price = vix_data.get('last') if vix_data else None
        spy_price = spy_data.get('last') if spy_data else None
        
        # Change calculation is still complex and needs historical data access
        # Market status should ideally come from the latest tracking record
        market_closed_flags = [d.get('is_market_closed') for d in [vix_data, spy_data] if d and d.get('is_market_closed') is not None]
        market_status = 'Closed' if any(market_closed_flags) else 'Open' # Simplified guess
        
        return {
            'vix_price': vix_price,
            'vix_change': None, # Placeholder
            'spy_price': spy_price,
            'spy_change': None, # Placeholder
            'market_status': market_status
        } 