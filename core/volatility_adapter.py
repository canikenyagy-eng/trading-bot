"""
Volatility Adaptation - Volatility-Aware Decision Making.

Adjusts system behavior based on market volatility.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class VolatilityRegime:
    """Volatility regime classification."""
    
    regime: str  # "low", "normal", "high", "extreme"
    atr_ratio: float  # Current ATR / 20-period ATR
    recommended_tp_mult: float
    recommended_risk_mult: float
    max_hold_hours: int


class VolatilityAdapter:
    """Volatility adaptation engine."""
    
    def __init__(self):
        # Volatility thresholds (ATR ratio)
        self.low_threshold = 0.6
        self.high_threshold = 1.5
        self.extreme_threshold = 2.0
        
        # Adaptation multipliers
        self.low_tp_mult = 1.3
        self.normal_tp_mult = 1.0
        self.high_tp_mult = 0.8
        self.extreme_tp_mult = 0.5
        
        self.low_risk_mult = 1.2
        self.normal_risk_mult = 1.0
        self.high_risk_mult = 0.7
        self.extreme_risk_mult = 0.5
        
        # Time limits
        self.low_max_hours = 48
        self.normal_max_hours = 24
        self.high_max_hours = 12
        self.extreme_max_hours = 6
    
    def classify_regime(self, current_atr: float, average_atr: float) -> VolatilityRegime:
        """Classify volatility regime."""
        ratio = current_atr / average_atr if average_atr > 0 else 1.0
        
        if ratio < self.low_threshold:
            return VolatilityRegime(
                regime="low",
                atr_ratio=ratio,
                recommended_tp_mult=self.low_tp_mult,
                recommended_risk_mult=self.low_risk_mult,
                max_hold_hours=self.low_max_hours
            )
        elif ratio < self.high_threshold:
            return VolatilityRegime(
                regime="normal",
                atr_ratio=ratio,
                recommended_tp_mult=self.normal_tp_mult,
                recommended_risk_mult=self.normal_risk_mult,
                max_hold_hours=self.normal_max_hours
            )
        elif ratio < self.extreme_threshold:
            return VolatilityRegime(
                regime="high",
                atr_ratio=ratio,
                recommended_tp_mult=self.high_tp_mult,
                recommended_risk_mult=self.high_risk_mult,
                max_hold_hours=self.high_max_hours
            )
        else:
            return VolatilityRegime(
                regime="extreme",
                atr_ratio=ratio,
                recommended_tp_mult=self.extreme_tp_mult,
                recommended_risk_mult=self.extreme_risk_mult,
                max_hold_hours=self.extreme_max_hours
            )
    
    def adapt_score(
        self,
        score: float,
        regime: VolatilityRegime
    ) -> float:
        """Adapt score based on volatility."""
        # Reduce score in extreme volatility
        if regime.regime == "extreme":
            return score * 0.6
        elif regime.regime == "high":
            return score * 0.8
        
        return score
    
    def adapt_rr(
        self,
        base_rr: float,
        regime: VolatilityRegime
    ) -> float:
        """Adapt risk/reward based on volatility."""
        return base_rr * regime.recommended_tp_mult
    
    def adapt_timing(
        self,
        age_seconds: float,
        regime: VolatilityRegime
    ) -> bool:
        """Check if trade should be closed based on volatility and time."""
        max_seconds = regime.max_hold_hours * 3600
        
        if age_seconds > max_seconds:
            return True
        
        return False
    
    def get_signal_adjustments(
        self,
        signal,
        current_atr: float,
        average_atr: float
    ) -> Dict[str, Any]:
        """Get all volatility adjustments for signal."""
        regime = self.classify_regime(current_atr, average_atr)
        
        current_score = getattr(signal, 'confidence', 0.5)
        adapted_score = self.adapt_score(current_score, regime)
        
        base_rr = getattr(signal, 'rr', 1.5)
        adapted_rr = self.adapt_rr(base_rr, regime)
        
        return {
            "regime": regime.regime,
            "atr_ratio": regime.atr_ratio,
            "original_score": current_score,
            "adapted_score": adapted_score,
            "score_change": adapted_score - current_score,
            "original_rr": base_rr,
            "adapted_rr": adapted_rr,
            "max_hold_hours": regime.max_hold_hours,
            "reductions": {
                "score": 1.0 - adapted_score / current_score if current_score > 0 else 0,
                "rr": 1.0 - adapted_rr / base_rr if base_rr > 0 else 0,
            }
        }


# Volatility Adapter End