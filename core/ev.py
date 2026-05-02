"""
Expected Value Engine - Trade EV Calculation.

This module calculates the expected value (EV) of a trade
using probabilities and risk/reward ratios.

EV Formula: EV = (P_tp × R) - (P_sl × 1)
Where R = risk/reward ratio
"""

from typing import Dict, Optional
from dataclasses import dataclass

from core.signal_engine import SignalEvaluation, Probabilities
from core import probability as prob_engine
from config import feature_flags as ff


@dataclass
class EVModel:
    """Model parameters for EV calculation."""
    
    # Base expectation adjustment
    base_adjustment: float = 0.0
    
    # Minimum EV to accept signals
    min_ev: float = -0.1  # Allow slightly negative to capture edge cases


class ExpectedValueEngine:
    """Engine for calculating trade expected value."""
    
    def __init__(self, model: Optional[EVModel] = None):
        self.model = model or EVModel()
        self.enabled = ff.ENABLE_EV
        self.min_ev = ff.MIN_EV
    
    def calculate_ev(
        self,
        signal: SignalEvaluation
    ) -> float:
        """Calculate expected value for a signal.
        
        Args:
            signal: SignalEvaluation
            
        Returns:
            Expected value
        """
        if not self.enabled:
            return 0.0
        
        probabilities = signal.probabilities
        rr = signal.rr
        
        # EV = (P_tp × RR) - (P_sl × 1)
        ev = (probabilities.tp_hit * rr) - (probabilities.sl_hit * 1.0)
        
        # Apply base adjustment
        ev += self.model.base_adjustment
        
        # Apply confidence weighting
        ev *= signal.confidence
        
        signal.expected_value = ev
        
        return ev
    
    def evaluate_ev(
        self,
        signal: SignalEvaluation
    ) -> tuple[bool, str]:
        """Evaluate if signal EV meets threshold.
        
        Args:
            signal: SignalEvaluation
            
        Returns:
            Tuple of (passes, reason if fails)
        """
        ev = signal.expected_value
        
        if ev < self.min_ev:
            return False, f"ev_below_minimum ({ev:.3f} < {self.min_ev})"
        
        return True, ""
    
    def meets_threshold(
        self,
        signal: SignalEvaluation
    ) -> bool:
        """Check if signal EV meets threshold.
        
        Args:
            signal: SignalEvaluation
            
        Returns:
            True if passes
        """
        passes, _ = self.evaluate_ev(signal)
        return passes
    
    def calculate_ev_components(
        self,
        signal: SignalEvaluation
    ) -> Dict[str, float]:
        """Get EV calculation components.
        
        Args:
            signal: SignalEvaluation
            
        Returns:
            Dictionary of EV components
        """
        prob = signal.probabilities
        rr = signal.rr
        
        return {
            "tp_contribution": prob.tp_hit * rr,
            "sl_contribution": -prob.sl_hit * 1.0,
            "base_adjustment": self.model.base_adjustment,
            "confidence_factor": signal.confidence,
            "total_ev": signal.expected_value,
        }
    
    def calculate_breakeven_rr(
        self,
        probability: float
    ) -> float:
        """Calculate breakeven R-multiple for a probability.
        
        Args:
            probability: Win probability
            
        Returns:
            Breakeven R-multiple
        """
        if probability >= 1.0:
            return 0.0
        
        return probability / (1.0 - probability)
    
    def get_required_rr(
        self,
        probability: float,
        min_ev: float = 0.0
    ) -> float:
        """Calculate required R-multiple for target EV.
        
        Args:
            probability: Win probability
            min_ev: Minimum expected value
            
        Returns:
            Required R-multiple
        """
        if probability <= 0.0:
            return float('inf')
        
        # EV = P × RR - (1-P) >= min_ev
        # RR >= (min_ev + 1 - P) / P
        return (min_ev + 1.0 - probability) / probability


# Expected Value Engine End