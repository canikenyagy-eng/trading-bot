"""
Backtest Validation Engine - Historical Validation with Comprehensive Metrics.

This module validates trading strategies using historical data with
extensive metrics: win rate, profit factor, drawdown, regime breakdown,
session breakdown, and stability analysis.

CRITICAL: Validation only. No live trading.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import statistics

from core.signal_engine import SignalEvaluation, Direction
from analytics.journaling import TradeJournal
from analytics.performance import PerformanceAnalyzer, PerformanceMetrics
from config import feature_flags as ff


@dataclass
class BacktestValidationResult:
    """Complete backtest validation result."""
    
    # Overall metrics
    total_trades: int = 0
    win_rate: float = 0.0
    avg_r: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    
    # Per regime
    by_regime: Dict[str, PerformanceMetrics] = field(default_factory=dict)
    
    # Per session
    by_session: Dict[str, PerformanceMetrics] = field(default_factory=dict)
    
    # Per symbol
    by_symbol: Dict[str, PerformanceMetrics] = field(default_factory=dict)
    
    # Per feature
    by_feature: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Stability
    rolling_winrates: List[float] = field(default_factory=list)
    stability_score: float = 0.0
    
    # Variance
    variance: float = 0.0
    
    # Rejected features
    rejected_features: List[str] = field(default_factory=list)
    
    # Timestamp
    validated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_trades": self.total_trades,
            "win_rate": self.win_rate,
            "avg_r": self.avg_r,
            "profit_factor": self.profit_factor,
            "max_drawdown": self.max_drawdown,
            "by_regime": {k: v.to_dict() for k, v in self.by_regime.items()},
            "by_session": {k: v.to_dict() for k, v in self.by_session.items()},
            "by_symbol": {k: v.to_dict() for k, v in self.by_symbol.items()},
            "by_feature": self.by_feature,
            "rolling_winrates": self.rolling_winrates,
            "stability_score": self.stability_score,
            "variance": self.variance,
            "rejected_features": self.rejected_features,
            "validated_at": self.validated_at.isoformat(),
        }


class BacktestValidationEngine:
    """Engine for validating strategies via backtesting.
    
    CRITICAL: Validation only. Does NOT execute trades.
    """
    
    def __init__(self):
        # Journal for trades
        self.journal = TradeJournal()
        self.analyzer = PerformanceAnalyzer(self.journal)
        
        # Validation parameters
        self.min_trades_for_validation = 20
        self.min_trades_per_regime = 5
        self.min_trades_per_session = 3
        self.stability_threshold = 0.3  # Below this, feature is rejected
        self.winrate_threshold = 0.40   # Below this, feature is rejected
        
        # Results storage
        self.results: List[BacktestValidationResult] = []
    
    def validate_signals(
        self,
        signals: List[SignalEvaluation],
        regime_data: Optional[Dict[str, str]] = None,
        session_data: Optional[Dict[str, str]] = None
    ) -> BacktestValidationResult:
        """Validate signals via backtesting.
        
        Args:
            signals: List of signals to validate
            regime_data: Optional regime data by signal_id
            session_data: Optional session data by signal_id
            
        Returns:
            BacktestValidationResult with comprehensive metrics
        """
        result = BacktestValidationResult()
        
        if not signals:
            return result
        
        # Record signals and simulate outcomes
        self._simulate_and_record(signals)
        
        # Get all outcomes
        outcomes = self.journal.outcomes
        
        if len(outcomes) < self.min_trades_for_validation:
            result.total_trades = len(outcomes)
            return result
        
        # Calculate overall metrics
        result.total_trades = len(outcomes)
        
        # Win rate
        wins = [o for o in outcomes if o["result"] == "tp"]
        result.win_rate = len(wins) / len(outcomes)
        
        # Average R
        result.avg_r = sum(o["rr_achieved"] for o in outcomes) / len(outcomes)
        
        # Profit factor
        profits = sum(o["rr_achieved"] for o in wins)
        losses = sum(o["rr_achieved"] for o in outcomes if o["result"] == "sl")
        if losses != 0:
            result.profit_factor = abs(profits / losses)
        
        # Max drawdown
        result.max_drawdown = self._calculate_max_drawdown(outcomes)
        
        # Regime breakdown
        if regime_data:
            result.by_regime = self._group_by_regime(outcomes, regime_data)
        
        # Session breakdown
        if session_data:
            result.by_session = self._group_by_session(outcomes, session_data)
        
        # Symbol breakdown
        result.by_symbol = self._group_by_symbol(outcomes)
        
        # Feature breakdown
        result.by_feature = self._analyze_features(signals, outcomes)
        
        # Rolling metrics
        result.rolling_winrates = self._calculate_rolling_winrates(outcomes)
        result.stability_score = self._calculate_stability(result.rolling_winrates)
        result.variance = self._calculate_variance(result.rolling_winrates)
        
        # Reject unstable features
        result.rejected_features = self._identify_rejected_features(result)
        
        # Store result
        self.results.append(result)
        
        return result
    
    def _simulate_and_record(
        self,
        signals: List[SignalEvaluation]
    ) -> None:
        """Simulate trades and record outcomes."""
        for signal in signals:
            if not signal.is_accepted:
                continue
            
            # Simulate outcome (simplified)
            # In real backtest, we'd use actual price data
            self.journal.add_signal(signal)
            
            # For now, record mock outcome based on confidence
            # (this would be replaced with actual price simulation)
            tp_prob = signal.probabilities.tp_hit if signal.probabilities else 0.5
            result = "tp" if tp_prob > 0.5 else "sl"
            rr = tp_prob * signal.rr - (1 - tp_prob)
            
            self.journal.record_outcome(
                signal.signal_id,
                signal.symbol,
                signal.direction.value,
                signal.entry,
                signal.tp_levels[0] if signal.tp_levels else signal.entry,
                result,
                rr
            )
    
    def _group_by_regime(
        self,
        outcomes: List[Dict],
        regime_data: Dict[str, str]
    ) -> Dict[str, PerformanceMetrics]:
        """Group outcomes by regime."""
        grouped = defaultdict(list)
        
        for outcome in outcomes:
            signal_id = outcome.get("signal_id", "")
            regime = regime_data.get(signal_id, "unknown")
            grouped[regime].append(outcome)
        
        results = {}
        for regime, regime_outcomes in grouped.items():
            if len(regime_outcomes) >= self.min_trades_per_regime:
                metrics = self.analyzer.calculate_metrics(regime_outcomes)
                results[regime] = metrics
        
        return results
    
    def _group_by_session(
        self,
        outcomes: List[Dict],
        session_data: Dict[str, str]
    ) -> Dict[str, PerformanceMetrics]:
        """Group outcomes by session."""
        grouped = defaultdict(list)
        
        for outcome in outcomes:
            signal_id = outcome.get("signal_id", "")
            session = session_data.get(signal_id, "unknown")
            grouped[session].append(outcome)
        
        results = {}
        for session, session_outcomes in grouped.items():
            if len(session_outcomes) >= self.min_trades_per_session:
                metrics = self.analyzer.calculate_metrics(session_outcomes)
                results[session] = metrics
        
        return results
    
    def _group_by_symbol(
        self,
        outcomes: List[Dict]
    ) -> Dict[str, PerformanceMetrics]:
        """Group outcomes by symbol."""
        grouped = defaultdict(list)
        
        for outcome in outcomes:
            symbol = outcome.get("symbol", "unknown")
            grouped[symbol].append(outcome)
        
        results = {}
        for symbol, symbol_outcomes in grouped.items():
            metrics = self.analyzer.calculate_metrics(symbol_outcomes)
            results[symbol] = metrics
        
        return results
    
    def _analyze_features(
        self,
        signals: List[SignalEvaluation],
        outcomes: List[Dict]
    ) -> Dict[str, Dict[str, float]]:
        """Analyze performance by feature."""
        feature_stats = defaultdict(lambda: {"wins": 0, "total": 0, "rr_total": 0.0})
        
        for signal in signals:
            if not signal.is_accepted:
                continue
            
            # Find outcome
            outcome = next(
                (o for o in outcomes if o.get("signal_id") == signal.signal_id),
                None
            )
            
            if outcome is None:
                continue
            
            # Analyze each feature present
            for feature_name, feature in signal.features.items():
                if feature.present:
                    feature_stats[feature_name]["total"] += 1
                    if outcome["result"] == "tp":
                        feature_stats[feature_name]["wins"] += 1
                    feature_stats[feature_name]["rr_total"] += outcome["rr_achieved"]
        
        # Calculate metrics
        results = {}
        for feature, stats in feature_stats.items():
            total = stats["total"]
            if total > 0:
                results[feature] = {
                    "winrate": stats["wins"] / total,
                    "avg_rr": stats["rr_total"] / total,
                    "count": total,
                }
        
        return results
    
    def _calculate_rolling_winrates(
        self,
        outcomes: List[Dict],
        window: int = 10
    ) -> List[float]:
        """Calculate rolling win rates."""
        winrates = []
        
        for i in range(window, len(outcomes) + 1):
            window_outcomes = outcomes[i-window:i]
            wins = sum(1 for o in window_outcomes if o["result"] == "tp")
            winrates.append(wins / window)
        
        return winrates
    
    def _calculate_stability(
        self,
        winrates: List[float]
    ) -> float:
        """Calculate stability score (0-1, higher is more stable)."""
        if not winrates or len(winrates) < 2:
            return 0.5
        
        variance = statistics.variance(winrates)
        stability = max(0, 1 - variance * 10)
        
        return stability
    
    def _calculate_variance(
        self,
        winrates: List[float]
    ) -> float:
        """Calculate variance in win rates."""
        if not winrates or len(winrates) < 2:
            return 0.0
        
        return statistics.variance(winrates)
    
    def _calculate_max_drawdown(
        self,
        outcomes: List[Dict]
    ) -> float:
        """Calculate maximum drawdown."""
        if not outcomes:
            return 0.0
        
        equity = 10000  # Starting balance
        peak = equity
        max_dd = 0.0
        
        for outcome in outcomes:
            equity += outcome["rr_achieved"] * (equity * 0.02)  # 2% risk
            
            if equity > peak:
                peak = equity
            
            dd = (peak - equity) / peak
            if dd > max_dd:
                max_dd = dd
        
        return max_dd
    
    def _identify_rejected_features(
        self,
        result: BacktestValidationResult
    ) -> List[str]:
        """Identify features that should be rejected."""
        rejected = []
        
        for feature, stats in result.by_feature.items():
            wr = stats.get("winrate", 0.5)
            count = stats.get("count", 0)
            
            # Need minimum samples
            if count < 10:
                continue
            
            # Check win rate
            if wr < self.winrate_threshold:
                rejected.append(f"{feature}_low_winrate")
        
        # Check stability
        if result.stability_score < self.stability_threshold:
            rejected.append("low_stability")
        
        return rejected
    
    def get_validation_summary(
        self,
        result: BacktestValidationResult
    ) -> str:
        """Get human-readable validation summary."""
        lines = [
            "=== Backtest Validation Summary ===",
            f"Total Trades: {result.total_trades}",
            f"Win Rate: {result.win_rate:.1%}",
            f"Avg R: {result.avg_r:.2f}",
            f"Profit Factor: {result.profit_factor:.2f}",
            f"Max Drawdown: {result.max_drawdown:.1%}",
            f"Stability: {result.stability_score:.2f}",
            "",
        ]
        
        if result.rejected_features:
            lines.append("Rejected Features:")
            for f in result.rejected_features:
                lines.append(f"  - {f}")
        
        return "\n".join(lines)


# Backtest Validation End