"""
Example usage of the DatabaseManager class.
This module demonstrates how to use the database functionality for trade management.
"""

from datetime import datetime, timedelta
from db_manager import DatabaseManager

def main():
    # Initialize the database manager
    db = DatabaseManager()
    
    # Example 1: Save a new bull put spread trade
    bull_put_trade = {
        'symbol': 'SPY',
        'underlying_price': 470.50,
        'trade_type': 'BULL_PUT',
        'expiration_date': '2024-05-17',
        'short_put': 460.0,
        'long_put': 455.0,
        'short_put_symbol': 'SPY240517P460000',
        'long_put_symbol': 'SPY240517P455000',
        'short_call': None,
        'long_call': None,
        'short_call_symbol': None,
        'long_call_symbol': None,
        'net_credit': 1.25,
        'num_contracts': 1
    }
    
    trade_id = db.save_new_trade(bull_put_trade)
    print(f"Saved new trade with ID: {trade_id}")
    
    # Example 2: Save an iron condor trade
    iron_condor_trade = {
        'symbol': 'QQQ',
        'underlying_price': 380.75,
        'trade_type': 'IRON_CONDOR',
        'expiration_date': '2024-05-17',
        'short_put': 370.0,
        'long_put': 365.0,
        'short_put_symbol': 'QQQ240517P370000',
        'long_put_symbol': 'QQQ240517P365000',
        'short_call': 390.0,
        'long_call': 395.0,
        'short_call_symbol': 'QQQ240517C390000',
        'long_call_symbol': 'QQQ240517C395000',
        'net_credit': 1.50,
        'num_contracts': 1
    }
    
    trade_id2 = db.save_new_trade(iron_condor_trade)
    print(f"Saved new trade with ID: {trade_id2}")
    
    # Example 3: Get all active trades
    active_trades = db.get_active_trades()
    print("\nActive trades:")
    for trade in active_trades:
        print(f"- {trade['symbol']} {trade['trade_type']}, "
              f"Expires: {trade['expiration_date']}, "
              f"Credit: ${trade['net_credit']:.2f}")
    
    # Example 4: Update trade status
    db.update_trade_status(trade_id, 'CLOSING')
    print(f"\nUpdated trade {trade_id} status to CLOSING")
    
    # Example 5: Complete a trade
    exit_data = {
        'underlying_exit_price': 472.25,
        'exit_debit': 0.50,
        'actual_profit_loss': 75.0,  # (1.25 - 0.50) * 100
        'exit_type': 'CLOSED_EARLY'
    }
    
    db.complete_trade(trade_id, exit_data)
    print(f"Completed trade {trade_id}")
    
    # Example 6: Get trades expiring soon
    expiring_trades = db.get_trades_expiring_soon(days=30)
    print("\nTrades expiring in next 30 days:")
    for trade in expiring_trades:
        print(f"- {trade['symbol']} expires on {trade['expiration_date']}")
    
    # Example 7: Get performance stats
    stats = db.get_trade_performance_stats()
    print("\nOverall performance stats:")
    print(f"Total trades: {stats['total_trades']}")
    print(f"Win rate: {stats['win_rate']:.1f}%")
    print(f"Total P&L: ${stats['total_profit_loss']:.2f}")
    
    # Example 8: Get P&L summary for current month
    today = datetime.now()
    first_of_month = today.replace(day=1).strftime('%Y-%m-%d')
    summary = db.get_profit_loss_summary(start_date=first_of_month)
    
    print(f"\nP&L Summary for {today.strftime('%B %Y')}:")
    print(f"Period P&L: ${summary['period_profit_loss']:.2f}")
    print(f"Number of trades: {summary['trade_count']}")
    print("\nBreakdown by trade type:")
    for trade_type, stats in summary['profit_by_type'].items():
        print(f"{trade_type}: {stats['count']} trades, "
              f"P&L: ${stats['profit_loss']:.2f}")

if __name__ == '__main__':
    main() 