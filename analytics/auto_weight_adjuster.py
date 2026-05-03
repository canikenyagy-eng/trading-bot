"""
Auto Feature Weight Adjustment - Adaptive Weight System.

Automatically adjusts feature weights based on performance.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from analytics.deep_feature_tracker import DeepFeatureTracker


@dataclass
class WeightAdjustment:
    """Weight adjustment record."""
    
    feature: str
    old_weight: float
    new_weight: float
    reason: str


class AutoWeightAdjuster:
    """Auto weight adjustment engine."""
    
    def __init__(self):
        self.tracker = DeepFeatureTracker()
        
        # Adjustment config
        self.adaptation_rate = 0.05  # 5% per update
        self.max_weight = 2.0  # Max 2x base
        self.min_weight = 0.3  # Min 30% base
        
        # Base weights
        self.base_weights = {
            "structure": 1.5,
            "liquidity": 1.2,
            "order_block": 1.3,
            "fvg": 1.0,
            "mitigation": 1.1,
            "regime_fit": 0.8,
            "entry_quality": 1.0,
            "smt": 0.7,
        }
        
        # Current weights
        self.current_weights = dict(self.base_weights)
        
        # History
        self.adjustment_history: List[WeightAdjustment] = []
        
        # Minimum samples before adjustment
        self.min_samples = 20
    
    def record_trade(
        self,
        features: Dict[str, Any],
        won: bool,
        rr: float = 0.0
    ) -> None:
        """Record trade for feature tracking."""
        self.tracker.record_trade(features, won, rr)
    
    def calculate_new_weights(self) -> Dict[str, float]:
        """Calculate new weights based on performance."""
        new_weights = dict(self.base_weights)
        
        # Get feature rankings
        ranking = self.tracker.get_feature_ranking()
        
        for item in ranking:
            feature = item["feature"]
            winrate = item["winrate"]
            avg_r = item["avg_r"]
            stability = item["stability"]
            
            if feature not in self.base_weights:
                continue
            
            base = self.base_weights[feature]
            
            # Calculate adjustment
            # Positive: improve weight
            # Negative: decrease weight
            adjustment = 0.0
            
            # Win rate adjustment
            if winrate > 0.55:
                adjustment += self.adaptation_rate
            elif winrate < 0.40:
                adjustment -= self.adaptation_rate
            
            # R adjustment
            if avg_r > 0.3:
                adjustment += self.adaptation_rate
            elif avg_r < 0.0:
                adjustment -= self.adaptation_rate
            
            # Apply adjustment
            new_weight = base * (1 + adjustment)
            
            # Clip
            new_weight = max(base * self.min_weight, min(base * self.max_weight, new_weight))
            
            new_weights[feature] = new_weight
        
        return new_weights
    
    def apply_adjustments(self) -> List[WeightAdjustment]:
        """Apply weight adjustments."""
        new_weights = self.calculate_new_weights()
        
        adjustments = []
        
        for feature, new_weight in new_weights.items():
            old_weight = self.current_weights.get(feature, self.base_weights[feature])
            
            # Record if changed
            if abs(new_weight - old_weight) > 0.01:
                reason = "improved" if new_weight > old_weight else "degraded"
                
                adjustments.append(WeightAdjustment(
                    feature=feature,
                    old_weight=old_weight,
                    new_weight=new_weight,
                    reason=reason
                ))
                
                self.current_weights[feature] = new_weight
                self.adjustment_history.append(adjustments[-1])
        
        return adjustments
    
    def get_weights(self) -> Dict[str, float]:
        """Get current feature weights."""
        return dict(self.current_weights)
    
    def reset_weights(self) -> None:
        """Reset weights to base."""
        self.current_weights = dict(self.base_weights)
        self.adjustment_history.clear()
    
    def get_adjustment_report(self) -> Dict[str, Any]:
        """Get adjustment report."""
        ranking = self.tracker.get_feature_ranking()
        
        return {
            "current_weights": self.current_weights,
            "base_weights": self.base_weights,
            "total_adjustments": len(self.adjustment_history),
            "ranking": ranking[:5],
        }


# Auto Weight Adjuster End