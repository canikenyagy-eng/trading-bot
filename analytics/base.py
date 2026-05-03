"""
Analytics Base - Independent Analytics without Circular Imports.

This module provides core analytics functionality without importing
from core modules, avoiding circular import issues.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import statistics
import math


@dataclass
class OutcomeRecord:
    """Individual trade outcome record."""
    signal_id: str = ""
    symbol: str = ""
    direction: str = ""
    entry: float = 0.0
    exit: float = 0.0
    result: str = ""  # "tp", "sl", "be"
    rr_achieved: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    features: Dict[str, bool] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "entry": self.entry,
            "exit": self.exit,
            "result": self.result,
            "rr_achieved": self.rr_achieved,
            "timestamp": self.timestamp.isoformat(),
            "features": self.features,
        }


@dataclass
class MFE_MAE:
    """Maximum Favorable Excursion / Maximum Adverse Excursion."""
    
    mfe: float = 0.0      # Max profit during trade
    mae: float = 0.0      # Max loss during trade
    mfe_pips: float = 0.0
    mae_pips: float = 0.0
    
    @property
    def mfe_mae_ratio(self) -> float:
        if self.mae != 0:
            return abs(self.mfe / self.mae)
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "mfe": self.mfe,
            "mae": self.mae,
            "mfe_pips": self.mfe_pips,
            "mae_pips": self.mae_pips,
            "mfe_mae_ratio": self.mfe_mae_ratio,
        }


@dataclass 
class PerformanceMetrics:
    """Comprehensive performance metrics."""
    
    # Basic metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    # Rate metrics
    win_rate: float = 0.0
    loss_rate: float = 0.0
    
    # R metrics
    avg_r: float = 0.0
    max_r: float = 0.0
    min_r: float = 0.0
    
    # Profit metrics
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_profit: float = 0.0
    profit_factor: float = 0.0
    
    # Drawdown
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    
    # Streak metrics
    max_winning_streak: int = 0
    max_losing_streak: int = 0
    
    # Time metrics
    avg_time_to_target: float = 0.0  # In bars
    avg_time_to_stop: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "loss_rate": self.loss_rate,
            "avg_r": self.avg_r,
            "max_r": self.max_r,
            "min_r": self.min_r,
            "gross_profit": self.gross_profit,
            "gross_loss": self.gross_loss,
            "net_profit": self.net_profit,
            "profit_factor": self.profit_factor,
            "max_drawdown": self.max_drawdown,
            "current_drawdown": self.current_drawdown,
            "max_winning_streak": self.max_winning_streak,
            "max_losing_streak": self.max_losing_streak,
            "avg_time_to_target": self.avg_time_to_target,
            "avg_time_to_stop": self.avg_time_to_stop,
        }


class AnalyticsEngine:
    """Independent analytics engine.
    
    Does NOT import from core modules to avoid circular imports.
    """
    
    def __init__(self):
        self.outcomes: List[OutcomeRecord] = []
        self.equity_curve: List[float] = [10000.0]  # Start with 10k
    
    def add_outcome(self, outcome: OutcomeRecord) -> None:
        """Add an outcome record."""
        self.outcomes.append(outcome)
        
        # Update equity curve
        last_equity = self.equity_curve[-1]
        risk_pct = 0.02  # 2% risk per trade
        new_equity = last_equity * (1 + outcome.rr_achieved * risk_pct)
        self.equity_curve.append(new_equity)
    
    def calculate_metrics(self) -> PerformanceMetrics:
        """Calculate comprehensive metrics."""
        if not self.outcomes:
            return PerformanceMetrics()
        
        metrics = PerformanceMetrics()
        metrics.total_trades = len(self.outcomes)
        
        # Categorize
        wins = [o for o in self.outcomes if o.result == "tp"]
        losses = [o for o in self.outcomes if o.result == "sl"]
        bes = [o for o in self.outcomes if o.result == "be"]
        
        metrics.winning_trades = len(wins)
        metrics.losing_trades = len(losses)
        
        # Win rate
        if metrics.total_trades > 0:
            metrics.win_rate = metrics.winning_trades / metrics.total_trades
            metrics.loss_rate = metrics.losing_trades / metrics.total_trades
        
        # R metrics
        all_rr = [o.rr_achieved for o in self.outcomes]
        metrics.avg_r = statistics.mean(all_rr) if all_rr else 0.0
        metrics.max_r = max(all_rr) if all_rr else 0.0
        metrics.min_r = min(all_rr) if all_rr else 0.0
        
        # Profit metrics
        metrics.gross_profit = sum(o.rr_achieved for o in wins) if wins else 0.0
        metrics.gross_loss = sum(o.rr_achieved for o in losses) if losses else 0.0
        metrics.net_profit = metrics.gross_profit + metrics.gross_loss
        
        if abs(metrics.gross_loss) > 0:
            metrics.profit_factor = metrics.gross_profit / abs(metrics.gross_loss)
        
        # Drawdown
        metrics.max_drawdown = self._calculate_max_drawdown()
        metrics.current_drawdown = self._calculate_current_drawdown()
        
        # Streaks
        metrics.max_winning_streak = self._calculate_max_streak("tp")
        metrics.max_losing_streak = self._calculate_max_streak("sl")
        
        return metrics
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown from equity curve."""
        if len(self.equity_curve) < 2:
            return 0.0
        
        peak = self.equity_curve[0]
        max_dd = 0.0
        
        for equity in self.equity_curve:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak
            if dd > max_dd:
                max_dd = dd
        
        return max_dd
    
    def _calculate_current_drawdown(self) -> float:
        """Calculate current drawdown."""
        if len(self.equity_curve) < 2:
            return 0.0
        
        peak = max(self.equity_curve)
        current = self.equity_curve[-1]
        
        return (peak - current) / peak if peak > 0 else 0.0
    
    def _calculate_max_streak(self, result: str) -> int:
        """Calculate maximum streak."""
        if not self.outcomes:
            return 0
        
        max_streak = 0
        current_streak = 0
        
        for outcome in self.outcomes:
            if outcome.result == result:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        
        return max_streak
    
    def calculate_by_symbol(self) -> Dict[str, PerformanceMetrics]:
        """Calculate metrics by symbol."""
        by_symbol = defaultdict(list)
        
        for outcome in self.outcomes:
            by_symbol[outcome.symbol].append(outcome)
        
        results = {}
        for symbol, outcomes in by_symbol.items():
            engine = AnalyticsEngine()
            engine.outcomes = outcomes
            results[symbol] = engine.calculate_metrics()
        
        return results
    
    def calculate_by_feature(
        self,
        feature_name: str
    ) -> Dict[str, Any]:
        """Calculate metrics by feature presence."""
        with_feature = [o for o in self.outcomes if o.features.get(feature_name)]
        without_feature = [o for o in self.outcomes if not o.features.get(feature_name)]
        
        results = {
            "with_feature": {
                "count": len(with_feature),
                "win_rate": self._calc_winrate(with_feature),
                "avg_r": self._calc_avg_r(with_feature),
            },
            "without_feature": {
                "count": len(without_feature),
                "win_rate": self._calc_winrate(without_feature),
                "avg_r": self._calc_avg_r(without_feature),
            }
        }
        
        return results
    
    def _calc_winrate(self, outcomes: List[OutcomeRecord]) -> float:
        if not outcomes:
            return 0.0
        wins = sum(1 for o in outcomes if o.result == "tp")
        return wins / len(outcomes)
    
    def _calc_avg_r(self, outcomes: List[OutcomeRecord]) -> float:
        if not outcomes:
            return 0.0
        return statistics.mean([o.rr_achieved for o in outcomes])
    
    def calculate_rolling_metrics(
        self,
        window: int = 20
    ) -> List[Dict[str, Any]]:
        """Calculate rolling window metrics."""
        if len(self.outcomes) < window:
            return []
        
        rolling = []
        
        for i in range(window, len(self.outcomes) + 1):
            window_outcomes = self.outcomes[i-window:i]
            engine = AnalyticsEngine()
            engine.outcomes = window_outcomes
            metrics = engine.calculate_metrics()
            
            rolling.append({
                "index": i,
                "metrics": metrics.to_dict(),
            })
        
        return rolling
    
    def get_stability_score(self, window: int = 50) -> float:
        """Calculate stability score based on variance.
        
        Returns 0-1, higher is more stable.
        """
        if len(self.outcomes) < 10:
            return 0.5
        
        recent = self.outcomes[-window:]
        
        if len(recent) < 10:
            return 0.5
        
        # Calculate rolling win rates
        win_rates = []
        
        for i in range(10, len(recent) + 1):
            window_trades = recent[i-10:i]
            wins = sum(1 for t in window_trades if t.result == "tp")
            win_rates.append(wins / 10)
        
        if not win_rates:
            return 0.5
        
        # Variance calculation
        variance = statistics.variance(win_rates) if len(win_rates) > 1 else 0
        
        # Lower variance = higher stability
        stability = max(0, 1 - variance * 10)
        
        return stability
    
    def get_expectancy(self) -> float:
        """Calculate expected value (average R per trade)."""
        if not self.outcomes:
            return 0.0
        return statistics.mean([o.rr_achieved for o in self.outcomes])


# Analytics Base End