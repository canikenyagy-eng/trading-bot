"""
Deep Feature Performance Tracker - Per-Feature Analytics.

Tracks detailed performance per feature for continuous improvement.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque


@dataclass
class DeepFeatureStats:
    """Deep feature statistics."""
    
    feature: str
    count: int = 0
    wins: int = 0
    total_rr: float = 0.0
    
    # Stability
    recent_wr: deque = field(default_factory=lambda: deque(maxlen=20))
    recent_rr: deque = field(default_factory=lambda: deque(maxlen=20))
    
    # Contribution
    dd_contribution: float = 0.0
    
    @property
    def winrate(self) -> float:
        return self.wins / self.count if self.count > 0 else 0.5
    
    @property
    def avg_r(self) -> float:
        return self.total_rr / self.count if self.count > 0 else 0.0
    
    @property
    def stability(self) -> float:
        if len(self.recent_wr) < 5:
            return 0.5
        
        wr = list(self.recent_wr)
        mean = sum(wr) / len(wr)
        variance = sum((w - mean) ** 2 for w in wr) / len(wr)
        
        return max(0.0, 1.0 - variance * 4)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature": self.feature,
            "count": self.count,
            "winrate": self.winrate,
            "avg_r": self.avg_r,
            "stability": self.stability,
            "dd_contribution": self.dd_contribution,
        }


class DeepFeatureTracker:
    """Deep feature performance tracker."""
    
    def __init__(self):
        self.features: Dict[str, DeepFeatureStats] = {}
        
        # Thresholds
        self.weak_threshold = 0.40  # 40% winrate
        self.degradation_threshold = 0.10  # 10% drop
        self.min_samples = 10
    
    def record_trade(
        self,
        features: Dict[str, Any],
        won: bool,
        rr: float = 0.0
    ) -> None:
        """Record trade result per feature."""
        for feature_name, feature_data in features.items():
            # Initialize if needed
            if feature_name not in self.features:
                self.features[feature_name] = DeepFeatureStats(feature=feature_name)
            
            stats = self.features[feature_name]
            
            # Update counts
            stats.count += 1
            if won:
                stats.wins += 1
            
            # Update R
            stats.total_rr += rr
            
            # Update recent windows for stability
            stats.recent_wr.append(1.0 if won else 0.0)
            stats.recent_rr.append(rr)
    
    def record_drawdown(self, feature_name: str, dd: float) -> None:
        """Record drawdown contribution from feature."""
        if feature_name in self.features:
            self.features[feature_name].dd_contribution = dd
    
    def get_stats(self, feature_name: str) -> Optional[DeepFeatureStats]:
        """Get stats for feature."""
        return self.features.get(feature_name)
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """Get all feature stats."""
        return {
            name: stats.to_dict()
            for name, stats in self.features.items()
            if stats.count >= self.min_samples
        }
    
    def get_feature_ranking(self) -> List[Dict]:
        """Rank features by performance."""
        ranking = []
        
        for name, stats in self.features.items():
            if stats.count < self.min_samples:
                continue
            
            ranking.append({
                "feature": name,
                "winrate": stats.winrate,
                "avg_r": stats.avg_r,
                "stability": stats.stability,
                "edge_score": stats.winrate * 0.5 + (stats.avg_r + 1) / 2 * 0.3 + stats.stability * 0.2,
            })
        
        ranking.sort(key=lambda x: x["edge_score"], reverse=True)
        return ranking
    
    def get_weak_features(self) -> List[str]:
        """Get weak features below threshold."""
        weak = []
        
        for name, stats in self.features.items():
            if stats.count < self.min_samples:
                continue
            
            if stats.winrate < self.weak_threshold:
                weak.append(name)
        
        return weak
    
    def get_improving_features(self) -> List[str]:
        """Get features showing improvement."""
        improving = []
        
        for name, stats in self.features.items():
            if stats.count < self.min_samples * 2:
                continue
            
            # Compare recent vs older
            recent_wr = list(stats.recent_wr)[-10:]
            older_wr = list(stats.recent_wr)[:-10]
            
            if not older_wr:
                continue
            
            recent_avg = sum(recent_wr) / len(recent_wr)
            older_avg = sum(older_wr) / len(older_wr)
            
            if recent_avg > older_avg + 0.05:
                improving.append(name)
        
        return improving
    
    def get_degrading_features(self) -> List[str]:
        """Get features showing degradation."""
        degrading = []
        
        for name, stats in self.features.items():
            if stats.count < self.min_samples * 2:
                continue
            
            recent_wr = list(stats.recent_wr)[-10:]
            older_wr = list(stats.recent_wr)[:-10]
            
            if not older_wr:
                continue
            
            recent_avg = sum(recent_wr) / len(recent_wr)
            older_avg = sum(older_wr) / len(older_wr)
            
            if recent_avg < older_avg - self.degradation_threshold:
                degrading.append(name)
        
        return degrading


# Deep Feature Tracker End