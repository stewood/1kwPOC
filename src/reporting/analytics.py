from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
import math
import logging

from .models import (
    RiskMetrics, 
    PerformanceMetrics, 
    TradeData, 
    CompletedTradeData,
    MarketContext
)
from ..logging_config import get_logger

# Initialize logger using the helper function
logger = get_logger(__name__)

class AnalyticsService:
    """Service for calculating advanced analytics and risk metrics."""
    
    def __init__(self, account_size: float = 50000.0):
        self.account_size = account_size
    
    def calculate_risk_metrics(
        self, 
        active_trades: List[TradeData], 
        completed_trades: List[CompletedTradeData]
    ) -> RiskMetrics:
        """Calculate risk metrics for the entire portfolio."""
        total_delta = sum(t.delta or 0 for t in active_trades)
        total_theta = sum(t.theta or 0 for t in active_trades)
        total_gamma = sum(
            sum(leg.gamma or 0 for leg in t.legs)
            for t in active_trades
        )
        total_vega = sum(
            sum(leg.vega or 0 for leg in t.legs)
            for t in active_trades
        )
        
        # Calculate position sizes
        total_risk = sum(abs(t.current_value) for t in active_trades)
        position_size_pct = (total_risk / self.account_size) * 100 if self.account_size > 0 else 0
        
        # Calculate max loss (minimum P&L value across all trades)
        min_active_pnl = min((t.pnl for t in active_trades), default=float('inf'))
        min_completed_pnl = min((t.actual_profit_loss for t in completed_trades), default=float('inf'))
        max_loss = min(min_active_pnl, min_completed_pnl)
        
        # Handle case where no trades exist
        if max_loss == float('inf'):
            max_loss = 0.0
        
        return RiskMetrics(
            total_delta=total_delta,
            total_theta=total_theta,
            total_gamma=total_gamma,
            total_vega=total_vega,
            position_size_pct=position_size_pct,
            max_loss=max_loss
        )
    
    def calculate_performance_metrics(
        self,
        active_trades: List[TradeData],
        completed_trades: List[CompletedTradeData]
    ) -> PerformanceMetrics:
        """Calculate performance metrics across all trades (active & completed)."""
        # Consider wins from both completed and active trades
        # For credit spreads: P&L > 0 is a win
        # For debit spreads: P&L > 0 is a win (same logic, but entry is negative)
        winning_completed = [t for t in completed_trades if t.actual_profit_loss > 0]
        winning_active = [t for t in active_trades if t.pnl > 0]
        total_winning_trades = len(winning_completed) + len(winning_active)
        
        # Base total trades on both active and completed for win rate calculation
        total_considered_trades = len(completed_trades) + len(active_trades)
        
        # Losing trades (only from completed for avg/gross loss)
        losing_trades = [t for t in completed_trades if t.actual_profit_loss <= 0]
        
        # Basic statistics
        win_rate = (total_winning_trades / total_considered_trades * 100) if total_considered_trades > 0 else 0
        
        # Profit metrics (based on completed trades only for realized gains/losses)
        # For both credit and debit spreads:
        # - Winning trades have positive P&L
        # - Losing trades have negative P&L
        gross_profit = sum(t.actual_profit_loss for t in winning_completed)
        gross_loss = abs(sum(t.actual_profit_loss for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
        
        # Size metrics (based on completed trades only)
        # For both credit and debit spreads:
        # - Winner size is the positive P&L
        # - Loser size is the absolute value of negative P&L
        avg_winner_size = gross_profit / len(winning_completed) if winning_completed else 0
        avg_loser_size = gross_loss / len(losing_trades) if losing_trades else 0
        largest_winner = max((t.actual_profit_loss for t in winning_completed), default=0)
        largest_loser = min((t.actual_profit_loss for t in losing_trades), default=0)
        
        # Time metrics (based on completed trades only)
        hold_times = [(t.close_date - t.entry_date).days for t in completed_trades]
        avg_hold_time = sum(hold_times) / len(hold_times) if hold_times else 0
        
        # Calculate periodic P&L (based on completed trades only)
        monthly_pnl = self._calculate_periodic_pnl(completed_trades, 'monthly')
        weekly_pnl = self._calculate_periodic_pnl(completed_trades, 'weekly')
        
        # Calculate Sharpe Ratio
        # For both credit and debit spreads:
        # - Returns are based on P&L percentage
        # - P&L percentage is calculated using absolute value of entry credit/debit
        returns = [t.profit_loss_percent for t in completed_trades]
        if returns:
            avg_return = sum(returns) / len(returns)
            std_dev = math.sqrt(sum((r - avg_return) ** 2 for r in returns) / len(returns))
            sharpe_ratio = (avg_return / std_dev) if std_dev != 0 else 0
        else:
            sharpe_ratio = 0
        
        return PerformanceMetrics(
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            avg_hold_time=avg_hold_time,
            win_rate=win_rate,
            avg_winner_size=avg_winner_size,
            avg_loser_size=avg_loser_size,
            largest_winner=largest_winner,
            largest_loser=largest_loser,
            monthly_pnl=monthly_pnl,
            weekly_pnl=weekly_pnl
        )
    
    def _calculate_periodic_pnl(
        self,
        completed_trades: List[CompletedTradeData],
        period: str
    ) -> Dict[str, float]:
        """Calculate P&L grouped by time period."""
        periodic_pnl = defaultdict(float)
        
        for trade in completed_trades:
            if period == 'monthly':
                key = trade.close_date.strftime('%Y-%m')
            else:  # weekly
                key = trade.close_date.strftime('%Y-%W')
            
            periodic_pnl[key] += trade.actual_profit_loss
        
        return dict(periodic_pnl)
    
    def calculate_correlation_matrix(
        self,
        active_trades: List[TradeData]
    ) -> Dict[str, Dict[str, float]]:
        """Calculate correlation matrix between different positions."""
        symbols = list({trade.symbol for trade in active_trades})
        matrix = defaultdict(dict)
        
        for i, symbol1 in enumerate(symbols):
            for symbol2 in symbols[i:]:
                trades1 = [t for t in active_trades if t.symbol == symbol1]
                trades2 = [t for t in active_trades if t.symbol == symbol2]
                
                if trades1 and trades2:
                    correlation = self._calculate_correlation(trades1, trades2)
                    matrix[symbol1][symbol2] = correlation
                    matrix[symbol2][symbol1] = correlation
        
        return dict(matrix)
    
    def _calculate_correlation(
        self,
        trades1: List[TradeData],
        trades2: List[TradeData]
    ) -> float:
        """Calculate correlation between two sets of trades."""
        # Simplified correlation based on P&L movements
        returns1 = [t.pnl_percent for t in trades1]
        returns2 = [t.pnl_percent for t in trades2]
        
        if not returns1 or not returns2:
            return 0
            
        mean1 = sum(returns1) / len(returns1)
        mean2 = sum(returns2) / len(returns2)
        
        variance1 = sum((r - mean1) ** 2 for r in returns1)
        variance2 = sum((r - mean2) ** 2 for r in returns2)
        
        if variance1 == 0 or variance2 == 0:
            return 0
            
        covariance = sum(
            (r1 - mean1) * (r2 - mean2)
            for r1, r2 in zip(returns1, returns2)
        )
        
        correlation = covariance / math.sqrt(variance1 * variance2)
        return max(min(correlation, 1), -1)  # Ensure result is between -1 and 1 