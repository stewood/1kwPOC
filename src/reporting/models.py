from dataclasses import dataclass, field
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
    volume: Optional[int] = None
    open_interest: Optional[int] = None
    implied_volatility: Optional[float] = None
    delta: Optional[float] = None
    theta: Optional[float] = None
    gamma: Optional[float] = None
    vega: Optional[float] = None

@dataclass
class RiskMetrics:
    """Risk analytics for a trade or portfolio."""
    total_delta: float = 0.0
    total_theta: float = 0.0
    total_gamma: float = 0.0
    total_vega: float = 0.0
    position_size_pct: float = 0.0  # As percentage of portfolio
    correlation_score: float = 0.0   # Correlation with other positions
    max_loss: float = 0.0
    probability_of_profit: Optional[float] = None

@dataclass
class PerformanceMetrics:
    """Performance analytics for a strategy or portfolio."""
    profit_factor: float = 0.0       # Gross profit / Gross loss
    sharpe_ratio: float = 0.0
    avg_hold_time: float = 0.0       # In days
    win_rate: float = 0.0
    avg_winner_size: float = 0.0
    avg_loser_size: float = 0.0
    largest_winner: float = 0.0
    largest_loser: float = 0.0
    monthly_pnl: Dict[str, float] = field(default_factory=dict)  # Format: "YYYY-MM": value
    weekly_pnl: Dict[str, float] = field(default_factory=dict)   # Format: "YYYY-WW": value

@dataclass
class CompletedTradeData:
    symbol: str
    entry_date: datetime
    expiration_date: datetime
    close_date: datetime
    entry_credit: float
    exit_debit: float
    actual_profit_loss: float
    profit_loss_percent: float
    strategy_type: str
    exit_type: str  # EXPIRED, CLOSED_EARLY, STOPPED_OUT, ROLLED
    num_contracts: int
    hold_time_days: int = 0  # New field
    risk_metrics: Optional[RiskMetrics] = None  # New field

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
    risk_metrics: Optional[RiskMetrics] = None  # New field
    delta: Optional[float] = None
    theta: Optional[float] = None

@dataclass
class StrategyData:
    name: str
    trades: List[TradeData]
    total_pnl: float
    win_rate: float
    active_count: int
    completed_trades: List[CompletedTradeData] = None
    performance_metrics: Optional[PerformanceMetrics] = None  # New field
    risk_metrics: Optional[RiskMetrics] = None  # New field

@dataclass
class MarketContext:
    """Current market environment data."""
    vix_price: float
    vix_change: float
    spy_price: float
    spy_change: float
    market_status: str
    notable_events: List[str] = field(default_factory=list)
    sector_performance: Dict[str, float] = field(default_factory=dict)
    market_breadth: Dict[str, float] = field(default_factory=dict)

@dataclass
class CompletedTrade:
    """Model for completed trade data."""
    symbol: str
    entry_date: datetime
    close_date: datetime
    entry_credit: float
    exit_debit: float
    pnl: float
    pnl_pct: float
    exit_type: str

@dataclass
class ReportData:
    """Model for report data."""
    # Core metrics
    total_pnl: float
    total_return: float
    active_trades: int
    completed_trades: int
    unique_underlyings: int
    win_rate: float
    avg_pnl_per_trade: float
    max_loss: float
    
    # Detailed data
    strategy_breakdown: dict
    completed_trades_list: List[CompletedTrade]
    strategies: Dict[str, StrategyData]
    
    # Enhanced analytics
    portfolio_risk_metrics: RiskMetrics
    portfolio_performance: PerformanceMetrics
    market_context: MarketContext
    
    # Time tracking
    report_date: datetime = datetime.now()
    generated_at: datetime = datetime.now()
    
    # Optional advanced analytics
    correlation_matrix: Optional[Dict[str, Dict[str, float]]] = None  # Symbol correlations
    risk_concentration: Optional[Dict[str, float]] = None  # Risk by underlying
    volatility_exposure: Optional[Dict[str, float]] = None  # Exposure by volatility level
    sector_exposure: Optional[Dict[str, float]] = None  # Exposure by sector 