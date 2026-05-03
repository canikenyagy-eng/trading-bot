"""
Edge Stability Filter - Penalize Unstable Feature Performance.

Penalizes signals with high winrate variance.
"""

from typing import Dict, List, Any
from dataclasses import dataclass, field
from collections import deque
import math

from config import feature_flags as ff


@dataclass
class FeatureStability:
    """Feature stability metrics."""
    
    feature: str
    recent_wr: deque = field(default_factory=lambda: deque(maxlen=50))
    
    @property
    def winrate(self) -> float:
        if not self.recent_wr:
            return 0.5
        return sum(self.recent_wr) / len(self.recent_wr)
    
    @property
    def variance(self) -> float:
        if len(self.recent_wr) < 5:
            return 0.0
        mean = self.winrate
        return sum((wr - mean) ** 2 for wr in self.recent_wr) / len(self.recent_wr)
    
    @property
    def stability(self) -> float:
        if self.variance == 0:
            return 1.0
        # Convert variance to stability (0-1)
        return max(0.0, 1.0 - self.variance * 4)


class EdgeStabilityFilter:
    """Edge stability filter."""
    
    def __init__(self):
        self.enabled = ff.ENABLE_EDGE_STABILITY
        
        # Thresholds
        self.variance_threshold = 0.04  # 4% max variance
        self.penalty_factor = 0.8
        
        # Feature tracking
        self.feature_stability: Dict[str, FeatureStability] = {}
    
    def record_outcome(self, features: Dict[str, Any], won: bool) -> None:
        """Record outcome for features."""
        if not self.enabled:
            return
        
        for name, data in features.items():
            if not isinstance(data, dict):
                continue
            
            # Initialize if needed
            if name not in self.feature_stability:
                self.feature_stability[name] = FeatureStability(feature=name)
            
            # Update winrate buffer
            winrate = 1.0 if won else 0.0
            self.feature_stability[name].recent_wr.append(winrate)
    
    def get_edge_consistency(
        self,
        features: Dict[str, Any]
    ) -> float:
        """Get edge consistency penalty."""
        if not self.enabled:
            return 1.0
        
        # Calculate combined stability
        if not features:
            return 1.0
        
        stability_scores = []
        
        for name, data in features.items():
            if not isinstance(data, dict):
                continue
            
            if name in self.feature_stability:
                stability = self.feature_stability[name].stability
                stability_scores.append(stability)
            else:
                # Unknown feature - use baseline
                stability_scores.append(0.8)
        
        if not stability_scores:
            return 1.0
        
        # Average stability
        avg = sum(stability_scores) / len(stability_scores)
        
        # Apply penalty for high variance
        if avg < 0.5:
            # High variance - apply stronger penalty
            return avg * 0.8
        
        return avg
    
    def apply_penalty(
        self,
        score: float,
        features: Dict[str, Any]
    ) -> float:
        """Apply stability penalty to score."""
        consistency = self.get_edge_consistency(features)
        
        # Only apply penalty for low consistency
        if consistency < self.variance_threshold:
            return score * consistency * self.penalty_factor
        
        return score
    
    def get_stability_report(self) -> Dict[str, Any]:
        """Get stability report."""
        if not self.enabled:
            return {"status": "disabled"}
        
        stability_data = {}
        
        for name, fs in self.feature_stability.items():
            if fs.recent_wr:
                stability_data[name] = {
                    "winrate": fs.winrate,
                    "variance": fs.variance,
                    "stability": fs.stability,
                    "samples": len(fs.recent_wr)
                }
        
        # Overall
        total_variance = sum(s.get("variance", 0) for s in stability_data.values())
        
        return {
            "total_features": len(stability_data),
            "average_variance": total_variance / max(1, len(stability_data)),
            "features": stability_data
        }


# Edge Stability Filter End