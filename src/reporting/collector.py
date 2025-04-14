from datetime import datetime
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import logging

from ..database.db_manager import DatabaseManager
from ..services.price_service import PriceService
from .analytics import AnalyticsService
from .models import (
    ReportData, StrategyData, TradeData, OptionLeg, 
    CompletedTradeData, CompletedTrade, MarketContext
)
from ..logging_config import get_logger

# Initialize logger using the helper function
logger = get_logger(__name__)

class ReportDataCollector:
    def __init__(self, db_manager: DatabaseManager, price_service: PriceService, account_size: float = 50000.0):
        self.db = db_manager
        self.price_service = price_service
        self.analytics = AnalyticsService(account_size=account_size)
    
    def collect_data(self) -> ReportData:
        """Collect all data needed for the report."""
        try:
            active_trades = self.db.get_active_trades()
            completed_trades = self.db.get_trade_history()
            logger.info(f"Collected {len(active_trades)} active trades and {len(completed_trades)} completed trades from DB.")
        except Exception as e:
            logger.error(f"Failed to get trades from database: {e}", exc_info=True)
            return self._create_empty_report()
        
        # Process trades by strategy
        strategies = self._process_trades_by_strategy(active_trades, completed_trades)
        
        # Calculate portfolio-wide metrics
        all_active_trades = [t for s in strategies.values() for t in s.trades]
        all_completed_trades = [t for s in strategies.values() for t in (s.completed_trades or [])]
        
        # Calculate risk and performance metrics
        portfolio_risk = self.analytics.calculate_risk_metrics(all_active_trades, all_completed_trades)
        portfolio_performance = self.analytics.calculate_performance_metrics(all_active_trades, all_completed_trades)
        
        # Calculate correlation matrix
        correlation_matrix = self.analytics.calculate_correlation_matrix(all_active_trades)
        
        # Get market context
        market_context = self._get_market_context()
        
        # Calculate summary statistics
        total_pnl = sum(s.total_pnl for s in strategies.values())
        total_trades = len(all_active_trades) + len(all_completed_trades)
        winning_trades = sum(1 for t in all_active_trades if t.pnl > 0)
        winning_trades += sum(1 for t in all_completed_trades if t.actual_profit_loss > 0)
        
        # Calculate unique underlyings
        unique_underlyings = len({t.symbol for t in all_active_trades})
        unique_underlyings += len({t.symbol for t in all_completed_trades})
        
        logger.info(f"Report Data Summary: Total PnL=${total_pnl:.2f}, Total Trades={total_trades}, Win Rate={(winning_trades / total_trades * 100) if total_trades > 0 else 0:.1f}%")
        
        return ReportData(
            # Core metrics
            total_pnl=total_pnl,
            total_return=(total_pnl / self.analytics.account_size * 100) if self.analytics.account_size else 0,
            active_trades=len(all_active_trades),
            completed_trades=len(all_completed_trades),
            unique_underlyings=unique_underlyings,
            win_rate=portfolio_performance.win_rate,
            avg_pnl_per_trade=portfolio_performance.avg_winner_size,
            max_loss=portfolio_risk.max_loss,
            
            # Detailed data
            strategy_breakdown=self._calculate_strategy_breakdown(all_completed_trades),
            completed_trades_list=[self._convert_to_completed_trade(t) for t in all_completed_trades],
            strategies=strategies,
            
            # Enhanced analytics
            portfolio_risk_metrics=portfolio_risk,
            portfolio_performance=portfolio_performance,
            market_context=market_context,
            
            # Advanced analytics
            correlation_matrix=correlation_matrix,
            risk_concentration=self._calculate_risk_concentration(all_active_trades),
            volatility_exposure=self._calculate_volatility_exposure(all_active_trades),
            sector_exposure=self._calculate_sector_exposure(all_active_trades)
        )
    
    def _process_trades_by_strategy(
        self,
        active_trades: List[Dict],
        completed_trades: List[Dict]
    ) -> Dict[str, StrategyData]:
        """Process trades grouped by strategy."""
        strategy_trades = defaultdict(list)
        strategy_completed_trades = defaultdict(list)
        
        # Group trades by strategy
        for trade in active_trades:
            trade_type = trade.get('trade_type')
            if trade_type:
                strategy_trades[trade_type].append(trade)
            else:
                logger.warning(f"Trade ID {trade.get('trade_id')} missing trade_type, skipping.")
        
        for trade in completed_trades:
            trade_type = trade.get('trade_type')
            if trade_type:
                strategy_completed_trades[trade_type].append(trade)
            else:
                logger.warning(f"Completed Trade ID {trade.get('trade_id')} missing trade_type, skipping.")
        
        # Process each strategy
        strategies = {}
        for strategy_type in set(strategy_trades.keys()) | set(strategy_completed_trades.keys()):
            strategy_data = self._process_strategy(
                strategy_type,
                strategy_trades[strategy_type],
                strategy_completed_trades[strategy_type]
            )
            if strategy_data.trades or strategy_data.completed_trades:
                strategies[strategy_type] = strategy_data
        
        return strategies
    
    def _process_strategy(
        self,
        strategy_type: str,
        trades: List[Dict],
        completed_trades: List[Dict]
    ) -> StrategyData:
        """Process all trades for a given strategy."""
        processed_trades = []
        processed_completed = []
        
        # Process active trades
        for trade_dict in trades:
            try:
                trade_data = self._process_trade(trade_dict)
                if trade_data:
                    processed_trades.append(trade_data)
            except Exception as e:
                trade_id = trade_dict.get('trade_id', 'N/A')
                logger.error(f"Failed to process trade ID {trade_id}: {e}", exc_info=True)
        
        # Process completed trades
        for trade_dict in completed_trades:
            try:
                completed_trade = self._process_completed_trade(trade_dict)
                if completed_trade:
                    processed_completed.append(completed_trade)
            except Exception as e:
                trade_id = trade_dict.get('trade_id', 'N/A')
                logger.error(f"Failed to process completed trade ID {trade_id}: {e}", exc_info=True)
        
        # Calculate strategy metrics
        risk_metrics = self.analytics.calculate_risk_metrics(processed_trades, processed_completed)
        performance_metrics = self.analytics.calculate_performance_metrics(processed_trades, processed_completed)
        
        return StrategyData(
            name=strategy_type,
            trades=processed_trades,
            completed_trades=processed_completed,
            total_pnl=sum(t.pnl for t in processed_trades) + sum(t.actual_profit_loss for t in processed_completed),
            win_rate=performance_metrics.win_rate,
            active_count=len(processed_trades),
            risk_metrics=risk_metrics,
            performance_metrics=performance_metrics
        )
    
    def _get_market_context(self) -> MarketContext:
        """Get current market environment data."""
        market_data = self._get_market_data()  # Existing method
        
        return MarketContext(
            vix_price=market_data['vix_price'],
            vix_change=market_data['vix_change'],
            spy_price=market_data['spy_price'],
            spy_change=market_data['spy_change'],
            market_status=market_data['market_status']
        )
    
    def _calculate_risk_concentration(self, active_trades: List[TradeData]) -> Dict[str, float]:
        """Calculate risk concentration by underlying."""
        risk_by_symbol = defaultdict(float)
        total_risk = sum(abs(t.current_value) for t in active_trades)
        
        if total_risk == 0:
            return {}
            
        for trade in active_trades:
            risk_by_symbol[trade.symbol] += abs(trade.current_value)
        
        return {symbol: risk / total_risk * 100 for symbol, risk in risk_by_symbol.items()}
    
    def _calculate_volatility_exposure(self, active_trades: List[TradeData]) -> Dict[str, float]:
        """Calculate exposure by volatility level."""
        exposure_buckets = {
            'low': 0.0,    # IV < 20
            'medium': 0.0, # 20 <= IV < 40
            'high': 0.0    # IV >= 40
        }
        
        for trade in active_trades:
            avg_iv = sum((leg.implied_volatility or 0) for leg in trade.legs) / len(trade.legs)
            exposure = abs(trade.current_value)
            
            if avg_iv < 20:
                exposure_buckets['low'] += exposure
            elif avg_iv < 40:
                exposure_buckets['medium'] += exposure
            else:
                exposure_buckets['high'] += exposure
        
        total_exposure = sum(exposure_buckets.values())
        if total_exposure == 0:
            return exposure_buckets
            
        return {k: v / total_exposure * 100 for k, v in exposure_buckets.items()}
    
    def _calculate_sector_exposure(self, active_trades: List[TradeData]) -> Dict[str, float]:
        """Calculate exposure by sector."""
        # This would require sector mapping data
        # For now, return empty dict or mock data
        return {}
    
    def _create_empty_report(self) -> ReportData:
        """Create an empty report when data collection fails."""
        empty_market_context = MarketContext(
            vix_price=0.0,
            vix_change=0.0,
            spy_price=0.0,
            spy_change=0.0,
            market_status='Unknown'
        )
        
        return ReportData(
            total_pnl=0.0,
            total_return=0.0,
            active_trades=0,
            completed_trades=0,
            unique_underlyings=0,
            win_rate=0.0,
            avg_pnl_per_trade=0.0,
            max_loss=0.0,
            strategy_breakdown={},
            completed_trades_list=[],
            strategies={},
            portfolio_risk_metrics=self.analytics.calculate_risk_metrics([], []),
            portfolio_performance=self.analytics.calculate_performance_metrics([], []),
            market_context=empty_market_context
        )
    
    def _convert_to_completed_trade(self, trade: CompletedTradeData) -> CompletedTrade:
        """Convert CompletedTradeData to CompletedTrade for template rendering."""
        return CompletedTrade(
            symbol=trade.symbol,
            entry_date=trade.entry_date,
            close_date=trade.close_date,
            entry_credit=trade.entry_credit,
            exit_debit=trade.exit_debit,
            pnl=trade.actual_profit_loss,
            pnl_pct=trade.profit_loss_percent,
            exit_type=trade.exit_type
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
        net_entry_credit_per_contract = trade_dict.get('net_credit', 0.0)  # Can be negative for debit spreads

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
            ],
            'BULL_CALL': [
                ('short_call_symbol', 'short_call', True, 'call'),
                ('long_call_symbol', 'long_call', False, 'call'),
            ],
            'BEAR_PUT': [
                ('short_put_symbol', 'short_put', True, 'put'),
                ('long_put_symbol', 'long_put', False, 'put'),
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
        # Use absolute value for percentage calculation to handle both credits and debits
        denominator = abs(net_entry_credit_per_contract) * total_contracts * 100
        pnl_percent = (total_pnl / denominator * 100) if denominator != 0 else 0
        
        logger.debug(f"Trade ID {trade_id}: EntryCredit={net_entry_credit_per_contract:.2f}, CurrentValue={current_legs_value:.2f}, PnL/Contract={pnl_per_contract:.2f}, Total PnL={total_pnl:.2f}")

        return TradeData(
            symbol=symbol,
            expiration=expiration_date,
            days_left=(expiration_date - datetime.now()).days,
            entry_credit=net_entry_credit_per_contract * total_contracts * 100, # Total credit/debit
            current_value=-current_legs_value * total_contracts * 100, # Total current cost to close
            pnl=total_pnl,
            pnl_percent=pnl_percent,
            legs=legs,
            strategy_type=trade_type,
            # Fetching greeks for the whole position is complex, maybe add later
            delta=None, 
            theta=None
        )
    
    def _process_completed_trade(self, trade_dict: Dict) -> Optional[CompletedTradeData]:
        """Process a single completed trade dictionary."""
        try:
            # Parse dates, handling potential timestamps by taking only the date part
            entry_date_str = trade_dict['entry_date'].split(' ')[0]
            expiration_date_str = trade_dict['expiration_date'].split(' ')[0]
            close_date_str = trade_dict['close_date'].split(' ')[0]
            
            # Get entry credit (can be negative for debit spreads)
            entry_credit_total = trade_dict['entry_credit']
            
            # Calculate P&L percentage
            pnl = trade_dict['actual_profit_loss']
            # Avoid division by zero; use absolute value for percentage calculation
            profit_loss_percent = (pnl / abs(entry_credit_total) * 100) if entry_credit_total != 0 else 0.0

            return CompletedTradeData(
                symbol=trade_dict['symbol'],
                entry_date=datetime.strptime(entry_date_str, '%Y-%m-%d'),
                expiration_date=datetime.strptime(expiration_date_str, '%Y-%m-%d'),
                close_date=datetime.strptime(close_date_str, '%Y-%m-%d'),
                entry_credit=entry_credit_total,  # Use the actual value (can be negative)
                exit_debit=trade_dict['exit_debit'],
                actual_profit_loss=pnl,
                profit_loss_percent=profit_loss_percent,
                strategy_type=trade_dict['trade_type'],
                exit_type=trade_dict['exit_type'],
                num_contracts=trade_dict['num_contracts']
            )
        except Exception as e:
            logger.error(f"Error processing completed trade ID {trade_dict.get('trade_id', 'N/A')}: {e}", exc_info=True)
            return None
    
    def _get_market_data(self) -> dict:
        """Get current market data (reads from DB, with fallback)."""
        logger.warning("Attempting to get VIX/SPY from latest DB records.")
        vix_data = None
        spy_data = None
        try:
            # TODO: This assumes VIX/SPY symbols are tracked like options, which might not be true.
            # Need a different mechanism or store index prices separately.
            vix_data = self.db.get_latest_option_price_data('^VIX')
            spy_data = self.db.get_latest_option_price_data('SPY')
        except Exception as e:
            logger.error(f"Error querying market data from DB: {e}", exc_info=True)

        # Extract data with defaults for missing values
        vix_price = vix_data.get('last') if vix_data else 0.0
        spy_price = spy_data.get('last') if spy_data else 0.0
        
        # Change calculation is still complex and needs historical data access
        # Determine market status based on availability (crude guess)
        market_status = 'Open' if vix_data or spy_data else 'Unknown'
        # A slightly better guess might check if either is explicitly marked closed
        # market_closed_flags = [d.get('is_market_closed') for d in [vix_data, spy_data] if d and d.get('is_market_closed') is not None]
        # market_status = 'Closed' if any(market_closed_flags) else 'Open' if vix_data or spy_data else 'Unknown'
        
        return {
            'vix_price': vix_price,
            'vix_change': 0.0, # Placeholder, needs historical data
            'spy_price': spy_price,
            'spy_change': 0.0, # Placeholder, needs historical data
            'market_status': market_status
        }

    def _calculate_strategy_breakdown(self, completed_trades: List[CompletedTradeData]) -> Dict:
        """Calculates P&L breakdown by strategy."""
        breakdown = defaultdict(lambda: {'count': 0, 'pnl': 0, 'win_rate': 0})
        strategy_trade_lists = defaultdict(list)

        for trade in completed_trades:
            strategy_type = trade.strategy_type  # Use correct attribute
            breakdown[strategy_type]['count'] += 1
            breakdown[strategy_type]['pnl'] += trade.actual_profit_loss
            strategy_trade_lists[strategy_type].append(trade)
            
        # Calculate win rates for each strategy
        for strategy_type, trades_list in strategy_trade_lists.items():
            winning_trades = [t for t in trades_list if t.actual_profit_loss > 0]
            if trades_list: # Avoid division by zero
                breakdown[strategy_type]['win_rate'] = (len(winning_trades) / len(trades_list)) * 100
            
        return dict(breakdown) 