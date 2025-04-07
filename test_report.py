#!/usr/bin/env python3
"""
Test script to generate a sample P&L report without needing live market data.
"""

import os
import sys
from datetime import datetime, timedelta
from random import randint, uniform, choice

# Set up Python path to find the module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.reporting.models import ReportData, StrategyData, TradeData, OptionLeg
from src.reporting.generator import HTMLReportGenerator

def generate_mock_option_leg(symbol, expiration, is_call, is_short, base_price):
    """Generate a mock option leg."""
    strike = round(base_price * uniform(0.8, 1.2) / 5) * 5  # Round to nearest $5
    entry_price = uniform(1.0, 3.0)
    current_price = entry_price * uniform(0.5, 1.5)
    
    return OptionLeg(
        type='call' if is_call else 'put',
        strike=strike,
        is_short=is_short,
        entry_price=entry_price,
        current_price=current_price,
        expiration=expiration,
        symbol=f"{symbol}{'C' if is_call else 'P'}{strike}"
    )

def generate_mock_data():
    """Generate mock data for the report."""
    today = datetime.now()
    symbols = ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "AMZN", "META", "TSLA"]
    base_prices = {
        "SPY": 500, "QQQ": 400, "IWM": 200, "AAPL": 180, 
        "MSFT": 400, "AMZN": 180, "META": 500, "TSLA": 170
    }
    strategies = {
        "Iron Condors": [],
        "Bear Call Spreads": [],
        "Bull Put Spreads": []
    }
    
    # Generate random trades for each strategy
    for strategy_name in strategies:
        num_trades = randint(4, 12)
        
        for _ in range(num_trades):
            symbol = choice(symbols)
            days_to_expiry = randint(14, 120)
            expiration = today + timedelta(days=days_to_expiry)
            base_price = base_prices[symbol]
            
            # Generate option legs based on strategy
            legs = []
            if strategy_name == "Iron Condors":
                # Short call
                legs.append(generate_mock_option_leg(
                    symbol, expiration, True, True, base_price * 1.05
                ))
                # Long call
                legs.append(generate_mock_option_leg(
                    symbol, expiration, True, False, base_price * 1.1
                ))
                # Short put
                legs.append(generate_mock_option_leg(
                    symbol, expiration, False, True, base_price * 0.95
                ))
                # Long put
                legs.append(generate_mock_option_leg(
                    symbol, expiration, False, False, base_price * 0.9
                ))
            elif strategy_name == "Bear Call Spreads":
                # Short call
                legs.append(generate_mock_option_leg(
                    symbol, expiration, True, True, base_price * 1.05
                ))
                # Long call
                legs.append(generate_mock_option_leg(
                    symbol, expiration, True, False, base_price * 1.1
                ))
            else:  # Bull Put Spreads
                # Short put
                legs.append(generate_mock_option_leg(
                    symbol, expiration, False, True, base_price * 0.95
                ))
                # Long put
                legs.append(generate_mock_option_leg(
                    symbol, expiration, False, False, base_price * 0.9
                ))
            
            # Calculate P&L
            entry_credit = sum(-leg.entry_price if leg.is_short else leg.entry_price for leg in legs)
            current_value = sum(-leg.current_price if leg.is_short else leg.current_price for leg in legs)
            pnl = (entry_credit - current_value) * 100  # Convert to dollars
            pnl_percent = (pnl / (abs(entry_credit) * 100) * 100) if entry_credit != 0 else 0
            
            trade = TradeData(
                symbol=symbol,
                expiration=expiration,
                days_left=days_to_expiry,
                entry_credit=entry_credit,
                current_value=current_value,
                pnl=pnl,
                pnl_percent=pnl_percent,
                legs=legs,
                strategy_type=strategy_name,
                delta=uniform(-0.3, 0.3),
                theta=uniform(0.01, 0.05)
            )
            
            strategies[strategy_name].append(trade)
    
    # Process strategy statistics
    strategy_data = {}
    total_pnl = 0
    winning_trades = 0
    total_trades = 0
    max_loss = 0
    
    for name, trades in strategies.items():
        strategy_pnl = sum(t.pnl for t in trades)
        strategy_winners = sum(1 for t in trades if t.pnl > 0)
        
        strategy_data[name] = StrategyData(
            name=name,
            trades=trades,
            total_pnl=strategy_pnl,
            win_rate=(strategy_winners / len(trades) * 100) if trades else 0,
            active_count=len(trades)
        )
        
        total_pnl += strategy_pnl
        winning_trades += strategy_winners
        total_trades += len(trades)
        max_loss = min(max_loss, min((t.pnl for t in trades), default=0))
    
    # Create the report data object
    return ReportData(
        total_pnl=total_pnl,
        total_return=total_pnl / 50000 * 100,  # Assuming $50k account
        active_trades_count=total_trades,
        unique_underlyings=len(set(t.symbol for s in strategies.values() for t in s)),
        win_rate=(winning_trades / total_trades * 100) if total_trades > 0 else 0,
        avg_pnl_per_trade=total_pnl / total_trades if total_trades > 0 else 0,
        max_loss=max_loss,
        strategies=strategy_data,
        vix_price=14.32,
        vix_change=-0.45,
        spy_price=base_prices["SPY"],
        spy_change=0.75,
        market_status="Pre-Market",
        generated_at=datetime.now()
    )

if __name__ == "__main__":
    # Create output directory if it doesn't exist
    os.makedirs("reports", exist_ok=True)
    
    # Generate mock data
    mock_data = generate_mock_data()
    
    # Generate report
    generator = HTMLReportGenerator()
    output_path = os.path.join("reports", f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
    
    print(f"Generating test report with {mock_data.active_trades_count} trades...")
    generator.generate(mock_data, output_path)
    print(f"Report generated: {output_path}") 