"""
EV-Dominant Scoring - EV as Primary Decision Factor.

Applies EV dominance to scoring for better selection.
"""

from typing import Dict, Any

from config import feature_flags as ff


class EVDominanceScorer:
    """EV-dominant scoring engine."""
    
    def __init__(self):
        self.enabled = ff.ENABLE_EV_DOMINANCE
        
        # EV scaling
        self.ev_scale = 0.5  # How much EV affects score
        
        # EV threshold
        self.negative_penalty = 2.0  # Penalty for negative EV
    
    def calculate_ev_dominant_score(
        self,
        base_score: float,
        expected_value: float,
        probabilities: Dict[str, float] = None
    ) -> float:
        """Calculate EV-dominant score.
        
        Args:
            base_score: Base confidence score
            expected_value: Signal EV
            probabilities: TP/SL probabilities
            
        Returns:
            EV-adjusted score
        """
        if not self.enabled:
            return base_score
        
        # Normalize EV to 0-1 range
        # EV typically: -0.2 to +0.6
        ev_normalized = (expected_value + 0.3) / 0.9
        ev_normalized = max(0.0, min(1.0, ev_normalized))
        
        # Apply EV dominance
        # Positive EV: boost
        # Negative EV: penalty
        if expected_value > 0:
            # Boost for positive EV
            boost = (ev_normalized - 0.5) * self.ev_scale
            new_score = base_score * (1 + boost)
        else:
            # Penalty for negative EV
            penalty = (0.5 - ev_normalized) * self.negative_penalty
            new_score = base_score * (1 - penalty)
        
        return max(0.0, min(1.0, new_score))
    
    def get_ev_priority(
        self,
        expected_value: float
    ) -> str:
        """Get EV priority description."""
        if expected_value > 0.3:
            return "high_ev"
        elif expected_value > 0.1:
            return "positive_ev"
        elif expected_value > -0.1:
            return "neutral_ev"
        else:
            return "negative_ev"
    
    def should_reject(
        self,
        expected_value: float,
        min_ev: float = None
    ) -> bool:
        """Check if signal should be rejected due to EV."""
        if not self.enabled:
            return False
        
        threshold = min_ev or ff.MIN_EV
        return expected_value < threshold


# EV Dominance Scorer End