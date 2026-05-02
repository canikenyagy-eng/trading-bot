"""
Analytics Performance Module - Performance Metrics.

This module calculates comprehensive performance metrics.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import statistics

from analytics.journaling import TradeJournal


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
        }


class PerformanceAnalyzer:
    """Analyzer for trading performance."""
    
    def __init__(self, journal: Optional[TradeJournal] = None):
        self.journal = journal or TradeJournal()
    
    def calculate_metrics(
        self,
        outcomes: Optional[List[Dict]] = None
    ) -> PerformanceMetrics:
        """Calculate comprehensive metrics."""
        outcomes = outcomes or self.journal.outcomes
        
        if not outcomes:
            return PerformanceMetrics()
        
        metrics = PerformanceMetrics()
        metrics.total_trades = len(outcomes)
        
        # Categorize trades
        wins = [o for o in outcomes if o["result"] == "tp"]
        losses = [o for o in outcomes if o["result"] == "sl"]
        bes = [o for o in outcomes if o["result"] == "be"]
        
        metrics.winning_trades = len(wins)
        metrics.losing_trades = len(losses)
        
        # Win rate
        if metrics.total_trades > 0:
            metrics.win_rate = metrics.winning_trades / metrics.total_trades
            metrics.loss_rate = metrics.losing_trades / metrics.total_trades
        
        # R metrics
        all_rr = [o["rr_achieved"] for o in outcomes]
        metrics.avg_r = statistics.mean(all_rr) if all_rr else 0.0
        metrics.max_r = max(all_rr) if all_rr else 0.0
        metrics.min_r = min(all_rr) if all_rr else 0.0
        
        # Profit metrics
        metrics.gross_profit = sum(o["rr_achieved"] for o in wins) if wins else 0.0
        metrics.gross_loss = sum(o["rr_achieved"] for o in losses) if losses else 0.0
        metrics.net_profit = metrics.gross_profit + metrics.gross_loss
        
        if abs(metrics.gross_loss) > 0:
            metrics.profit_factor = metrics.gross_profit / abs(metrics.gross_loss)
        
        return metrics
    
    def calculate_rolling_metrics(
        self,
        window: int = 20
    ) -> List[Dict[str, Any]]:
        """Calculate rolling metrics."""
        if not self.journal.outcomes:
            return []
        
        rolling = []
        
        for i in range(window, len(self.journal.outcomes) + 1):
            window_outcomes = self.journal.outcomes[i-window:i]
            metrics = self.calculate_metrics(window_outcomes)
            
            rolling.append({
                "index": i,
                "metrics": metrics.to_dict(),
            })
        
        return rolling
    
    def get_stability_score(
        self,
        window: int = 50
    ) -> float:
        """Calculate stability score based on variance."""
        if not self.journal.outcomes:
            return 0.5
        
        recent = self.journal.outcomes[-window:]
        
        if len(recent) < 10:
            return 0.5
        
        # Calculate rolling win rates
        win_rates = []
        
        for i in range(10, len(recent) + 1):
            window_trades = recent[i-10:i]
            wins = sum(1 for t in window_trades if t["result"] == "tp")
            win_rates.append(wins / 10)
        
        if not win_rates:
            return 0.5
        
        # Variance calculation
        variance = statistics.variance(win_rates) if len(win_rates) > 1 else 0
        
        # Lower variance = higher stability
        stability = max(0, 1 - variance * 10)
        
        return stability
    
    def calculate_by_regime(
        self,
        regime_stats: Dict[str, List[Dict]]
    ) -> Dict[str, PerformanceMetrics]:
        """Calculate metrics by regime."""
        results = {}
        
        for regime, outcomes in regime_stats.items():
            results[regime] = self.calculate_metrics(outcomes)
        
        return results
    
    def calculate_by_session(
        self,
        session_stats: Dict[str, List[Dict]]
    ) -> Dict[str, PerformanceMetrics]:
        """Calculate metrics by session."""
        results = {}
        
        for session, outcomes in session_stats.items():
            results[session] = self.calculate_metrics(outcomes)
        
        return results


# Performance Module End