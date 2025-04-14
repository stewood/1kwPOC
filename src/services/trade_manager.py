"""
Trade Management Service

Handles the simulation of trade management tasks including:
- Monitoring active trades
- Managing trade lifecycle (entry to exit)
- Handling expiration
- Managing trade status updates
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from ..database.db_manager import DatabaseManager
from ..services.price_service import PriceService
from ..logging_config import get_logger

# Initialize logger using the helper function
logger = get_logger(__name__)

class TradeManager:
    """Service for managing active trades."""
    
    def __init__(self, db_manager: DatabaseManager, price_service: Optional[PriceService] = None):
        """Initialize the trade manager.
        
        Args:
            db_manager: Database manager instance
            price_service: Optional price service for real-time pricing
        """
        self.db = db_manager
        self.price_service = price_service
        
    def _parse_date(self, date_str: str) -> datetime:
        """Parse a date string into a datetime object.
        
        Handles both date-only and timestamp formats.
        
        Args:
            date_str: Date string in either 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' format
            
        Returns:
            datetime object
        """
        try:
            # Try parsing as timestamp first
            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                # Try parsing as date only
                return datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError as e:
                logger.error(f"Could not parse date string: {date_str}")
                raise e
        
    def process_active_trades(self) -> Dict[str, int]:
        """
        Process all active trades.
        
        Returns:
            Dictionary with processing statistics
        """
        stats = {
            'total_trades': 0,
            'active_trades': 0,
            'expired_trades': 0,
            'errors': 0
        }
        
        try:
            # Get all active trades
            active_trades = self.db.get_active_trades()
            stats['total_trades'] = len(active_trades)
            
            if not active_trades:
                logger.info("No active trades found")
                return stats
            
            # Process all trades
            for trade in active_trades:
                try:
                    # Get trade details
                    trade_id = trade['trade_id']
                    symbol = trade['symbol']
                    trade_type = trade['trade_type']
                    status = trade['status']
                    
                    # Convert string dates to datetime objects
                    expiration_date = self._parse_date(trade['expiration_date']) if isinstance(trade['expiration_date'], str) else trade['expiration_date']
                    entry_date = self._parse_date(trade['entry_date']) if isinstance(trade['entry_date'], str) else trade['entry_date']
                    
                    # Calculate days to expiry
                    days_to_expiry = (expiration_date - datetime.now()).days
                    
                    logger.info(f"\n📊 Processing Trade {trade_id}:")
                    logger.info(f"  Symbol: {symbol}")
                    logger.info(f"  Type: {trade_type}")
                    logger.info(f"  Status: {status}")
                    logger.info(f"  Entry Date: {entry_date.strftime('%Y-%m-%d')}")
                    logger.info(f"  Expiration Date: {expiration_date.strftime('%Y-%m-%d')}")
                    logger.info(f"  Days to Expiry: {days_to_expiry}")
                    
                    if days_to_expiry < 0:
                        logger.warning(f"⚠️ Trade {trade_id} has expired!")
                        
                        # Update status to EXPIRED
                        self.db.update_trade_status(trade_id, 'EXPIRED')
                        logger.info(f"Updated trade {trade_id} status to EXPIRED")
                        
                        # Calculate actual P&L for expired trades
                        actual_pnl = 0
                        if trade['spread_type'] == 'CREDIT':
                            actual_pnl = trade['net_credit'] * trade['num_contracts']
                        else:  # DEBIT
                            actual_pnl = -trade['net_credit'] * trade['num_contracts']
                        
                        # Prepare exit data for completed trades
                        exit_data = {
                            'underlying_exit_price': trade['underlying_price'],  # Use entry price as exit price for expired trades
                            'exit_debit': 0.0,  # For expired trades, exit debit is 0
                            'actual_profit_loss': actual_pnl,
                            'exit_type': 'EXPIRED'
                        }
                        
                        # Complete the trade
                        self.db.complete_trade(trade_id, exit_data)
                        logger.info(f"Completed expired trade {trade_id}")
                        
                        stats['expired_trades'] += 1
                        logger.info(f"\n✅ Successfully processed expired trade {trade_id}")
                        
                    else:
                        # Process active trade
                        logger.info(f"Processing active trade {trade_id}...")
                        self._process_active_trade(trade)
                        stats['active_trades'] += 1
                        logger.info(f"✅ Successfully processed active trade {trade_id}")
                        
                except Exception as e:
                    logger.error(f"❌ Error processing trade {trade_id}: {str(e)}")
                    logger.exception("Full traceback:")
                    stats['errors'] += 1
            
            # Log final statistics
            logger.info("\n📈 Processing Statistics:")
            for key, value in stats.items():
                logger.info(f"  {key}: {value}")
                
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error in process_active_trades: {str(e)}")
            logger.exception("Full traceback:")
            return stats
            
    def _process_active_trade(self, trade: Dict[str, Any]) -> None:
        """Process an active trade and display current status.
        
        Args:
            trade: Trade record from database
        """
        try:
            trade_id = trade['trade_id']
            symbol = trade['symbol']
            trade_type = trade['trade_type']
            net_entry_credit = trade.get('net_credit', 0.0)  # No longer using abs() to allow negative values
            total_contracts = trade.get('num_contracts', 1)
            
            logger.info(f"\n  ACTIVE TRADE SUMMARY:")
            logger.info(f"  Trade ID: {trade_id}")
            logger.info(f"  Symbol: {symbol}")
            logger.info(f"  Type: {trade_type}")
            logger.info(f"  Entry Credit/Debit: ${net_entry_credit:.2f}")
            
            # Get current prices for all legs
            current_legs_value = 0
            leg_definitions = {
                'BULL_PUT': [
                    ('Short Put', trade.get('short_put_symbol'), True),
                    ('Long Put', trade.get('long_put_symbol'), False)
                ],
                'BEAR_CALL': [
                    ('Short Call', trade.get('short_call_symbol'), True),
                    ('Long Call', trade.get('long_call_symbol'), False)
                ],
                'IRON_CONDOR': [
                    ('Short Put', trade.get('short_put_symbol'), True),
                    ('Long Put', trade.get('long_put_symbol'), False),
                    ('Short Call', trade.get('short_call_symbol'), True),
                    ('Long Call', trade.get('long_call_symbol'), False)
                ],
                'BULL_CALL': [
                    ('Short Call', trade.get('short_call_symbol'), True),
                    ('Long Call', trade.get('long_call_symbol'), False)
                ],
                'BEAR_PUT': [
                    ('Short Put', trade.get('short_put_symbol'), True),
                    ('Long Put', trade.get('long_put_symbol'), False)
                ]
            }
            
            if trade_type not in leg_definitions:
                logger.error(f"Unknown trade type: {trade_type}")
                return
                
            # Process each leg
            for leg_name, option_symbol, is_short in leg_definitions[trade_type]:
                if not option_symbol:
                    continue
                    
                try:
                    current_price = self.price_service.get_current_price(option_symbol)
                    if current_price is None:
                        logger.warning(f"Could not get current price for {option_symbol}")
                        continue
                        
                    # For short legs, current price represents a debit (cost to close)
                    # For long legs, current price represents a credit (value if closed)
                    multiplier = -1 if is_short else 1
                    current_legs_value += current_price * multiplier
                    
                    logger.info(f"  {leg_name}:")
                    logger.info(f"    Symbol: {option_symbol}")
                    logger.info(f"    Current Price: ${current_price:.2f}")
                    logger.info(f"    Value Contribution: ${current_price * multiplier:.2f}")
                    
                except Exception as e:
                    logger.error(f"Error processing leg {leg_name} for trade {trade_id}: {str(e)}")
                    continue
            
            # Calculate P&L
            # For credit spreads: PnL = Entry Credit - Current Value to Close
            # For debit spreads: PnL = -Entry Debit - Current Value to Close
            # Note: current_legs_value is already net (short legs are negative, long are positive)
            # so current net cost to close is -current_legs_value
            if trade.get('spread_type', 'CREDIT') == 'CREDIT':
                pnl_per_contract = net_entry_credit - (-current_legs_value)  # Credit received - cost to close
            else:  # DEBIT
                pnl_per_contract = -abs(net_entry_credit) - (-current_legs_value)  # -Debit paid - cost to close
            
            total_pnl = pnl_per_contract * total_contracts * 100  # Multiply by 100 for contract size
            
            # Calculate P&L percentage based on entry credit/debit
            # Use absolute value for percentage calculation to handle both credits and debits
            pnl_percent = (total_pnl / (abs(net_entry_credit) * total_contracts * 100)) * 100 if net_entry_credit != 0 else 0
            
            logger.info(f"\n  P&L Summary:")
            logger.info(f"  Entry Credit/Debit: ${net_entry_credit:.2f}")
            logger.info(f"  Current Value: ${current_legs_value:.2f}")
            logger.info(f"  P&L per Contract: ${pnl_per_contract:.2f}")
            logger.info(f"  Total P&L: ${total_pnl:.2f} ({pnl_percent:.1f}%)")
            
        except Exception as e:
            logger.error(f"Error processing active trade {trade_id}: {str(e)}")
            logger.error("Stack trace:", exc_info=True)
            
    def _process_expired_trade(self, trade: Dict[str, Any]) -> None:
        """Process an expired trade and display final P&L.
        
        Args:
            trade: Trade record from database
        """
        try:
            trade_id = trade['trade_id']
            symbol = trade['symbol']
            trade_type = trade['trade_type']
            
            # Convert string dates to datetime if needed
            expiration_date = self._parse_date(trade['expiration_date']) if isinstance(trade['expiration_date'], str) else trade['expiration_date']
            entry_date = self._parse_date(trade['entry_date']) if isinstance(trade['entry_date'], str) else trade['entry_date']
            
            # Calculate days held
            days_held = (expiration_date - entry_date).days
            
            logger.info(f"\n  EXPIRED TRADE SUMMARY:")
            logger.info(f"  Days Held: {days_held}")
            
            # Get historical prices at expiration
            logger.info(f"  Getting expiration price for {symbol} on {expiration_date.strftime('%Y-%m-%d')}")
            expiration_price = self.price_service.get_historical_price(
                symbol,
                expiration_date.strftime('%Y-%m-%d')
            )
            if expiration_price is None:
                logger.error(f"Could not get expiration price for {symbol}")
                return
            
            # Get entry price
            logger.info(f"  Getting entry price for {symbol} on {entry_date.strftime('%Y-%m-%d')}")
            entry_price = self.price_service.get_historical_price(
                symbol,
                entry_date.strftime('%Y-%m-%d')
            )
            if entry_price is None:
                logger.error(f"Could not get entry price for {symbol}")
                return
            
            # Calculate final P&L
            logger.info(f"  Calculating P&L:")
            logger.info(f"    Entry Price: ${entry_price:.2f}")
            logger.info(f"    Expiration Price: ${expiration_price:.2f}")
            
            pnl = expiration_price - entry_price
            pnl_percent = (pnl / entry_price) * 100
            
            logger.info(f"  Entry Price: ${entry_price:.2f}")
            logger.info(f"  Expiration Price: ${expiration_price:.2f}")
            logger.info(f"  Final P&L: ${pnl:.2f} ({pnl_percent:.1f}%)")
            
            # Get and display leg details if available
            if trade_type in ['BULL_PUT', 'BEAR_CALL', 'IRON_CONDOR']:
                self._display_leg_details(trade, expiration_date)
            
        except Exception as e:
            logger.error(f"Error processing expired trade {trade_id}: {str(e)}")
            logger.error("Stack trace:", exc_info=True)
            
    def _display_leg_details(self, trade: Dict[str, Any], expiration_date: datetime) -> None:
        """Display details for each option leg at expiration.
        
        Args:
            trade: Trade record from database
            expiration_date: Expiration date of the trade
        """
        try:
            # Get leg details
            legs = []
            if trade.get('short_put_symbol'):
                legs.append(('Short Put', trade['short_put_symbol'], True))
            if trade.get('long_put_symbol'):
                legs.append(('Long Put', trade['long_put_symbol'], False))
            if trade.get('short_call_symbol'):
                legs.append(('Short Call', trade['short_call_symbol'], True))
            if trade.get('long_call_symbol'):
                legs.append(('Long Call', trade['long_call_symbol'], False))
            
            # Display each leg
            for leg_name, symbol, is_short in legs:
                logger.info(f"\n  {leg_name} Details:")
                logger.info(f"    Symbol: {symbol}")
                
                # Get expiration price
                price = self.price_service.get_historical_price(
                    symbol,
                    expiration_date.strftime('%Y-%m-%d')
                )
                
                if price is not None:
                    logger.info(f"    Expiration Price: ${price:.2f}")
                    logger.info(f"    Value: ${price * (-1 if is_short else 1):.2f}")
                else:
                    logger.warning(f"    Could not get expiration price")
            
        except Exception as e:
            logger.error(f"Error displaying leg details: {str(e)}")
            logger.error("Stack trace:", exc_info=True) 