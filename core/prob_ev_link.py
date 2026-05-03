"""
Probability-EV Link - Consistency Checker.

Validates consistency between probability and EV.
"""

from typing import Dict, List, Any
from dataclasses import dataclass

from config import feature_flags as ff


@dataclass
class ConsistencyWarning:
    """Consistency warning."""
    
    type: str
    severity: str
    message: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "severity": self.severity,
            "message": self.message
        }


class ProbabilityEVLink:
    """Probability-EV consistency engine."""
    
    def __init__(self):
        self.enabled = ff.ENABLE_PROBABILITY_EV_LINK
        
        # Thresholds
        self.min_prob = ff.MIN_PROBABILITY
        self.consistency_threshold = 0.15  # Max difference
        
        # Warning severity
        self.warning_enabled = True
    
    def validate_consistency(
        self,
        expected_value: float,
        probabilities: Dict[str, float],
        avg_tp: float = 1.0,
        avg_sl: float = 1.0
    ) -> List[ConsistencyWarning]:
        """Validate EV-Probability consistency.
        
        Args:
            expected_value: Signal EV
            probabilities: {"tp_hit": float, "sl_hit": float}
            avg_tp: Average TP distance
            avg_sl: Average SL distance
            
        Returns:
            List of warnings
        """
        warnings = []
        
        if not self.enabled:
            return warnings
        
        tp_prob = probabilities.get('tp_hit', 0.5)
        
        # Calculate EV from probability
        sl_prob = probabilities.get('sl_hit', 0.5)
        
        calculated_ev = (tp_prob * avg_tp) - (sl_prob * avg_sl)
        
        # Check consistency
        ev_diff = abs(expected_value - calculated_ev)
        
        if ev_diff > self.consistency_threshold:
            severity = "high" if ev_diff > 0.25 else "medium"
            
            if expected_value > 0.1 and tp_prob < self.min_prob:
                # High EV but low probability - warning
                warnings.append(ConsistencyWarning(
                    type="ev_probability_conflict",
                    severity=severity,
                    message=f"Higher EV ({expected_value:.2f}) but low TP probability ({tp_prob:.0%})"
                ))
            
            elif expected_value < -0.1 and tp_prob > 0.5:
                warnings.append(ConsistencyWarning(
                    type="ev_probability_conflict",
                    severity=severity,
                    message=f"Negative EV ({expected_value:.2f}) but high TP probability ({tp_prob:.0%})"
                ))
        
        # Low probability warning
        if tp_prob < self.min_prob:
            warnings.append(ConsistencyWarning(
                type="low_probability",
                severity="low",
                message=f"TP probability {tp_prob:.0%} below threshold {self.min_prob:.0%}"
            ))
        
        return warnings
    
    def get_adjustment(
        self,
        expected_value: float,
        probability: float
    ) -> float:
        """Get probability adjustment based on EV."""
        if not self.enabled:
            return probability
        
        # If EV and probability mismatch, adjust probability
        if expected_value > 0.2 and probability < 0.4:
            # Boost probability
            adjustment = 0.1
            return min(1.0, probability + adjustment)
        
        elif expected_value < -0.1 and probability > 0.4:
            # Reduce probability
            adjustment = 0.1
            return max(0.0, probability - adjustment)
        
        return probability
    
    def add_warnings_to_signal(
        self,
        signal,
        expected_value: float = None,
        probabilities: Dict[str, float] = None
    ) -> None:
        """Add consistency warnings to signal."""
        if not self.enabled:
            return
        
        ev = expected_value or getattr(signal, 'expected_value', 0)
        probs = probabilities or getattr(signal, 'probabilities', {'tp_hit': 0.5})
        
        warnings = self.validate_consistency(ev, probs)
        
        if not hasattr(signal, 'warnings'):
            signal.warnings = []
        
        for warning in warnings:
            signal.warnings.append(warning.to_dict())


# Probability-EV Link End