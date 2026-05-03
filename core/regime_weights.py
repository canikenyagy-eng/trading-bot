"""
Regime-Adaptive Weights - Performance-Based Weight Adjustment.

Adjusts feature weights based on regime-specific performance.

CRITICAL: Analysis only - no auto-trading.
"""

from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

from config import feature_flags as ff


@dataclass
class RegimePerformance:
    """Performance by feature and regime."""
    
    regime: str = ""
    feature: str = ""
    wins: int = 0
    losses: int = 0
    
    @property
    def total(self) -> int:
        return self.wins + self.losses
    
    @property
    def winrate(self) -> float:
        if self.total == 0:
            return 0.5
        return self.wins / self.total
    
    @property
    def avg_r(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.wins - self.losses) / self.total
    
    def add_outcome(self, won: bool) -> None:
        if won:
            self.wins += 1
        else:
            self.losses += 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "regime": self.regime,
            "feature": self.feature,
            "total": self.total,
            "winrate": self.winrate,
            "avg_r": self.avg_r,
        }


class RegimeAdaptiveWeights:
    """Regime-adaptive weight engine."""
    
    def __init__(self):
        self.enabled = ff.ENABLE_META_ADAPTATION
        
        # Performance tracking
        self.performance: Dict[str, Dict[str, RegimePerformance]] = defaultdict(
            lambda: defaultdict(lambda: RegimePerformance())
        )
        
        # Base weights (from config)
        self.base_weights = dict(ff.DEFAULT_WEIGHTS)
        
        # Adaptation parameters
        self.min_samples = 10
        self.max_adjustment = 0.5  # Max +/- 50% adjustment
        self.adaptation_rate = 0.2  # How fast to adapt
    
    def _get_key(self, regime: str, feature: str) -> tuple:
        """Get performance key."""
        return (regime, feature)
    
    def record_outcome(
        self,
        features: Dict[str, Any],
        regime: str,
        result: str  # "tp", "sl", "be"
    ) -> None:
        """Record trade outcome by regime and feature.
        
        Args:
            features: Active feature breakdown dict
            regime: Current regime
            result: Trade outcome
        """
        if not self.enabled:
            return
        
        won = result == "tp"
        
        # Record for each active feature
        for feature_name, feature_data in features.items():
            if isinstance(feature_data, dict) and feature_data.get("present", False):
                perf = self.performance[regime][feature_name]
                perf.regime = regime
                perf.feature = feature_name
                perf.add_outcome(won)
    
    def get_adjusted_weight(
        self,
        feature: str,
        regime: str,
        base_weight: float = 1.0
    ) -> float:
        """Get regime-adjusted weight.
        
        Args:
            feature: Feature name
            regime: Current regime
            base_weight: Base weight from config
            
        Returns:
            Adjusted weight
        """
        if not self.enabled:
            return base_weight
        
        if regime not in self.performance:
            return base_weight
        
        if feature not in self.performance[regime]:
            return base_weight
        
        perf = self.performance[regime][feature]
        
        # Not enough data
        if perf.total < self.min_samples:
            return base_weight
        
        # Calculate adjustment based on performance
        wr_delta = (perf.winrate - 0.5)  # 0 = baseline, positive = good
        avg_r_delta = perf.avg_r
        
        # Combined adjustment
        adjustment = (wr_delta * 0.5 + avg_r_delta * 0.5) * self.adaptation_rate
        
        # Cap adjustment
        adjustment = max(-self.max_adjustment, min(self.max_adjustment, adjustment))
        
        return base_weight * (1 + adjustment)
    
    def get_all_adjusted_weights(
        self,
        regime: str
    ) -> Dict[str, float]:
        """Get all weights adjusted for regime.
        
        Args:
            regime: Current regime
            
        Returns:
            Dict of feature -> adjusted weight
        """
        adjusted = {}
        
        for feature, base_weight in self.base_weights.items():
            adjusted[feature] = self.get_adjusted_weight(
                feature, regime, base_weight
            )
        
        return adjusted
    
    def get_performance_breakdown(
        self,
        regime: str
    ) -> Dict[str, Dict[str, Any]]:
        """Get performance breakdown by regime."""
        if regime not in self.performance:
            return {}
        
        breakdown = {}
        
        for feature, perf in self.performance[regime].items():
            if perf.total > 0:
                breakdown[feature] = perf.to_dict()
        
        return breakdown
    
    def get_regime_comparison(
        self,
        feature: str
    ) -> Dict[str, float]:
        """Compare feature performance across regimes."""
        comparison = {}
        
        for regime, features in self.performance.items():
            if feature in features:
                perf = features[feature]
                if perf.total >= self.min_samples:
                    comparison[regime] = perf.winrate
        
        return comparison
    
    def reset(self) -> None:
        """Reset all performance data."""
        self.performance.clear()


# Regime-Adaptive Weights End