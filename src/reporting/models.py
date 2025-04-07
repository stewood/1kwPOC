from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

@dataclass
class OptionLeg:
    type: str  # 'call' or 'put'
    strike: float
    is_short: bool
    entry_price: float
    current_price: float
    expiration: datetime
    symbol: str

@dataclass
class TradeData:
    symbol: str
    expiration: datetime
    days_left: int
    entry_credit: float
    current_value: float
    pnl: float
    pnl_percent: float
    legs: List[OptionLeg]
    strategy_type: str
    delta: Optional[float] = None
    theta: Optional[float] = None

@dataclass
class StrategyData:
    name: str
    trades: List[TradeData]
    total_pnl: float
    win_rate: float
    active_count: int

@dataclass
class ReportData:
    # Summary stats
    total_pnl: float
    total_return: float
    active_trades_count: int
    unique_underlyings: int
    win_rate: float
    avg_pnl_per_trade: float
    max_loss: float
    
    # Strategy-specific data
    strategies: Dict[str, StrategyData]
    
    # Market data
    vix_price: float
    vix_change: float
    spy_price: float
    spy_change: float
    market_status: str
    
    # Metadata
    generated_at: datetime 