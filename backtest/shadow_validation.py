"""
Shadow Validation Engine - Historical Validation without Pipeline Disruption.

Validates new features/algorithms on historical data without
affecting live signals.

CRITICAL: Validation only - no live impact.
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

from config import feature_flags as ff


@dataclass
class ValidationMetric:
    """Single validation metric."""
    
    name: str = ""
    value: float = 0.0
    baseline: float = 0.0
    change: float = 0.0  # Percentage change
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "baseline": self.baseline,
            "change": self.change,
        }


@dataclass
class ValidationResult:
    """Complete validation result."""
    
    feature_name: str = ""
    
    # Performance metrics
    win_rate: float = 0.0
    avg_r: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    total_trades: int = 0
    
    # Stability
    variance: float = 0.0
    stability_score: float = 0.0
    
    # Comparison
    baseline_metrics: Dict[str, float] = field(default_factory=dict)
    improvement: Dict[str, float] = field(default_factory=dict)
    
    # Status
    passed: bool = False
    status_message: str = ""
    recommendations: List[str] = field(default_factory=list)
    
    @property
    def is_positive(self) -> bool:
        """Check if improvement is positive."""
        return self.improvement.get("win_rate", 0) > 0 or self.improvement.get("avg_r", 0) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_name": self.feature_name,
            "win_rate": self.win_rate,
            "avg_r": self.avg_r,
            "profit_factor": self.profit_factor,
            "max_drawdown": self.max_drawdown,
            "total_trades": self.total_trades,
            "variance": self.variance,
            "stability_score": self.stability_score,
            "baseline_metrics": self.baseline_metrics,
            "improvement": self.improvement,
            "passed": self.passed,
            "status_message": self.status_message,
            "recommendations": self.recommendations,
        }


@dataclass
class ShadowValidationConfig:
    """Configuration for shadow validation."""
    
    # Thresholds
    min_improvement_wr: float = 0.02  # Min 2% WR improvement
    min_improvement_r: float = 0.05   # Min 0.05R improvement
    min_trades: int = 30              # Min trades for validation
    max_drawdown_threshold: float = 0.20  # Max 20% DD allowed
    
    # Stability requirements
    min_stability: float = 0.5       # Min stability score
    max_variance: float = 0.15         # Max variance allowed
    
    # Comparison baseline
    use_existing_performance: bool = True


class ShadowValidationEngine:
    """Shadow validation engine."""
    
    def __init__(self):
        self.enabled = True  # Always enabled for validation
        self.config = ShadowValidationConfig()
        
        # Validation results storage
        self.results: Dict[str, ValidationResult] = {}
        
        #历史 data buffer - структурированные данные для тестирования
        self.historical_data: List[Dict[str, Any]] = []
        
        # Baseline metrics (without new features)
        self.baseline_metrics: Dict[str, float] = {}
    
    def load_historical_data(
        self,
        data: List[Dict[str, Any]]
    ) -> None:
        """Load historical data for validation.
        
        Expected format:
        [
            {
                "symbol": "EURUSD",
                "direction": "long",
                "entry": 1.0850,
                "sl": 1.0820,
                "tp": 1.0900,
                "result": "tp",  # "tp", "sl", "be"
                "rr": 1.0,
                "features": {
                    "fvg": {"present": True, "strength": 0.8},
                    "ob": {"present": True, "strength": 0.7},
                },
                "regime": "trend",
                "timestamp": datetime,
            },
            ...
        ]
        """
        self.historical_data = data
        
        # Calculate baseline metrics
        self._calculate_baseline()
    
    def _calculate_baseline(self) -> None:
        """Calculate baseline metrics without new features."""
        if not self.historical_data:
            return
        
        trades = [t for t in self.historical_data if t.get("result")]
        
        if not trades:
            return
        
        # Win rate
        wins = sum(1 for t in trades if t["result"] == "tp")
        win_rate = wins / len(trades)
        
        # Average R
        rr_values = [t.get("rr", 0) for t in trades]
        avg_r = sum(rr_values) / len(rr_values)
        
        # Profit factor
        gross_profit = sum(t.get("rr", 0) for t in trades if t.get("rr", 0) > 0)
        gross_loss = abs(sum(t.get("rr", 0) for t in trades if t.get("rr", 0) < 0))
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Calculate variance of rolling win rates
        variance = self._calculate_variance(trades)
        
        # Drawdown
        drawdown = self._calculate_max_drawdown(trades)
        
        self.baseline_metrics = {
            "win_rate": win_rate,
            "avg_r": avg_r,
            "profit_factor": pf,
            "variance": variance,
            "max_drawdown": drawdown,
            "total_trades": len(trades),
        }
    
    def _calculate_variance(self, trades: List[Dict]) -> float:
        """Calculate variance of rolling win rates."""
        if len(trades) < 10:
            return 0.0
        
        window = 10
        win_rates = []
        
        for i in range(window, len(trades) + 1):
            window_trades = trades[i-window:i]
            wins = sum(1 for t in window_trades if t.get("result") == "tp")
            win_rates.append(wins / window)
        
        if len(win_rates) < 2:
            return 0.0
        
        # Calculate variance
        mean = sum(win_rates) / len(win_rates)
        variance = sum((wr - mean) ** 2 for wr in win_rates) / len(win_rates)
        
        return variance
    
    def _calculate_max_drawdown(self, trades: List[Dict]) -> float:
        """Calculate maximum drawdown."""
        if not trades:
            return 0.0
        
        equity = [10000]
        
        for trade in trades:
            rr = trade.get("rr", 0)
            new_equity = equity[-1] * (1 + rr * 0.02)  # 2% risk
            equity.append(new_equity)
        
        if len(equity) < 2:
            return 0.0
        
        peak = max(equity)
        current = equity[-1]
        
        return (peak - current) / peak
    
    def validate_feature(
        self,
        feature_name: str,
        filter_func: Callable[[Dict], bool],
        data: Optional[List[Dict]] = None
    ) -> ValidationResult:
        """Validate a feature using filter function.
        
        Args:
            feature_name: Name of feature being tested
            filter_func: Function that returns True if trade uses feature
            data: Optional historical data (uses loaded if not provided)
            
        Returns:
            ValidationResult with metrics
        """
        if data is None:
            data = self.historical_data
        
        result = ValidationResult(feature_name=feature_name)
        
        # Filter trades that use feature
        filtered_trades = [t for t in data if filter_func(t)]
        
        if len(filtered_trades) < self.config.min_trades:
            result.status_message = "insufficient_data"
            result.recommendations = [f"Need at least {self.config.min_trades} trades"]
            self.results[feature_name] = result
            return result
        
        # Calculate metrics for filtered trades
        wins = sum(1 for t in filtered_trades if t["result"] == "tp")
        result.win_rate = wins / len(filtered_trades)
        
        rr_values = [t.get("rr", 0) for t in filtered_trades]
        result.avg_r = sum(rr_values) / len(rr_values)
        
        gross_profit = sum(r for r in rr_values if r > 0)
        gross_loss = abs(sum(r for r in rr_values if r < 0))
        result.profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        result.total_trades = len(filtered_trades)
        
        # Variance
        result.variance = self._calculate_variance(filtered_trades)
        
        # Calculate stability (1 - variance, capped)
        result.stability_score = max(0, 1 - result.variance * 10)
        
        # Max drawdown
        result.max_drawdown = self._calculate_max_drawdown(filtered_trades)
        
        # Compare with baseline
        if self.baseline_metrics:
            result.baseline_metrics = self.baseline_metrics.copy()
            
            result.improvement = {
                "win_rate": result.win_rate - self.baseline_metrics.get("win_rate", 0),
                "avg_r": result.avg_r - self.baseline_metrics.get("avg_r", 0),
                "profit_factor": result.profit_factor - self.baseline_metrics.get("profit_factor", 0),
                "variance": self.baseline_metrics.get("variance", 0) - result.variance,
            }
        
        # Determine pass/fail
        result.passed = self._evaluate_result(result)
        
        # Set status message
        if result.passed:
            result.status_message = "passed"
        else:
            result.status_message = "failed"
        
        # Generate recommendations
        result.recommendations = self._generate_recommendations(result)
        
        self.results[feature_name] = result
        return result
    
    def _evaluate_result(self, result: ValidationResult) -> bool:
        """Evaluate if validation passed."""
        # Must have minimum trades
        if result.total_trades < self.config.min_trades:
            return False
        
        # Must pass stability check
        if result.stability_score < self.config.min_stability:
            return False
        
        # Must not exceed max drawdown
        if result.max_drawdown > self.config.max_drawdown_threshold:
            return False
        
        # Must show improvement in at least one metric
        has_improvement = (
            result.improvement.get("win_rate", 0) >= self.config.min_improvement_wr or
            result.improvement.get("avg_r", 0) >= self.config.min_improvement_r
        )
        
        return has_improvement
    
    def _generate_recommendations(
        self,
        result: ValidationResult
    ) -> List[str]:
        """Generate recommendations based on result."""
        recs = []
        
        if result.variance > self.config.max_variance:
            recs.append("high_variance_reduce_weight")
        
        if result.max_drawdown > self.config.max_drawdown_threshold * 0.8:
            recs.append("drawdown_warning")
        
        if result.improvement.get("win_rate", 0) < 0:
            recs.append("winrate_decreased_consider_disable")
        
        if result.improvement.get("avg_r", 0) < 0:
            recs.append("avg_r_decreased_review_feature")
        
        if result.stability_score < 0.6:
            recs.append("stability_low_monitor")
        
        if not recs:
            recs.append("feature_approved")
        
        return recs
    
    def validate_fvg_feature(self) -> ValidationResult:
        """Validate FVG feature."""
        def fvg_filter(trade: Dict) -> bool:
            features = trade.get("features", {})
            return features.get("fvg", {}).get("present", False)
        
        return self.validate_feature("fvg", fvg_filter)
    
    def validate_ob_feature(self) -> ValidationResult:
        """Validate Order Block feature."""
        def ob_filter(trade: Dict) -> bool:
            features = trade.get("features", {})
            return features.get("order_block", {}).get("present", False)
        
        return self.validate_feature("order_block", ob_filter)
    
    def validate_combination(
        self,
        feature_names: List[str]
    ) -> ValidationResult:
        """Validate feature combination."""
        combo_name = "+".join(feature_names)
        
        def combo_filter(trade: Dict) -> bool:
            features = trade.get("features", {})
            return all(
                features.get(name, {}).get("present", False)
                for name in feature_names
            )
        
        return self.validate_feature(combo_name, combo_filter)
    
    def validate_regime_feature(
        self,
        regime: str
    ) -> ValidationResult:
        """Validate feature in specific regime."""
        def regime_filter(trade: Dict) -> bool:
            return trade.get("regime") == regime
        
        return self.validate_feature(f"regime_{regime}", regime_filter)
    
    def get_all_results(self) -> Dict[str, Dict[str, Any]]:
        """Get all validation results."""
        return {name: result.to_dict() for name, result in self.results.items()}
    
    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary."""
        passed = [name for name, r in self.results.items() if r.passed]
        failed = [name for name, r in self.results.items() if not r.passed]
        
        total_improvement = {
            "win_rate": 0.0,
            "avg_r": 0.0,
        }
        
        for r in self.results.values():
            total_improvement["win_rate"] += r.improvement.get("win_rate", 0)
            total_improvement["avg_r"] += r.improvement.get("avg_r", 0)
        
        return {
            "total_validated": len(self.results),
            "passed": len(passed),
            "failed": len(failed),
            "passed_features": passed,
            "failed_features": failed,
            "total_improvement": total_improvement,
            "baseline": self.baseline_metrics,
        }
    
    def should_enable_feature(
        self,
        feature_name: str
    ) -> bool:
        """Check if feature should be enabled."""
        if feature_name not in self.results:
            return False
        
        return self.results[feature_name].passed


# Shadow Validation Engine End