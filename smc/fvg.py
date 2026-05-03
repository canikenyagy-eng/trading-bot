"""
SMC FVG Module - Fair Value Gap Detection.

Fair Value Gaps are areas of inefficiency where price has gapped
past without filling, often acting as future support/resistance.
"""

from typing import List, Optional
from dataclasses import dataclass

from core.signal_engine import FeatureBreakdown
from config import feature_flags as ff


@dataclass
class FVGEvent:
    """Fair Value Gap event."""
    
    # Gap boundaries
    low: float = 0.0
    mid: float = 0.0
    high: float = 0.0
    
    # Properties
    size: float = 0.0
    age: int = 0
    filled: bool = False
    
    # Direction
    direction: str = ""  # "bullish" or "bearish"
    
    def to_dict(self):
        return {
            "low": self.low,
            "mid": self.mid,
            "high": self.high,
            "size": self.size,
            "age": self.age,
            "filled": self.filled,
            "direction": self.direction,
        }


class FVGDetector:
    """Detector for Fair Value Gaps."""
    
    def __init__(self):
        self.enabled = ff.ENABLE_FVG
        
        # Parameters
        self.min_gap_size = 0.0005  # Minimum gap size (0.05%)
        self.max_gap_age = 10       # Max bars before gap considered old
        self.lookback = 20          # Bars to look for gaps
    
    def detect_fvg(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        current_price: float
    ) -> Optional[FVGEvent]:
        """Detect Fair Value Gap.
        
        Args:
            highs: High prices
            lows: Low prices
            closes: Close prices
            current_price: Current market price
            
        Returns:
            FVGEvent if FVG detected, None otherwise
        """
        if not self.enabled or len(highs) < 3:
            return None
        
        # Check recent bars for FVG pattern
        for i in range(len(highs) - 3, max(0, len(highs) - self.lookback) - 1, -1):
            # Bullish FVG: low of current bar > high of bar 2 ago (gap up)
            gap_low = lows[i]  # Current bar low
            gap_high = highs[i - 2]  # Bar 2 ago high
            
            if gap_low > gap_high:
                size = (gap_low - gap_high) / gap_high
                
                if size >= self.min_gap_size:
                    age = len(closes) - i - 1
                    
                    return FVGEvent(
                        low=gap_high,
                        mid=(gap_high + gap_low) / 2,
                        high=gap_low,
                        size=size,
                        age=age,
                        filled=self._is_filled(gap_high, gap_low, current_price),
                        direction="bullish"  # FIXED: gap up = bullish
                    )
            
            # Bearish FVG: high of current bar < low of bar 2 ago (gap down)
            gap_high = highs[i]  # Current bar high
            gap_low = lows[i - 2]  # Bar 2 ago low
            
            if gap_high < gap_low:
                size = (gap_low - gap_high) / gap_low
                
                if size >= self.min_gap_size:
                    age = len(closes) - i - 1
                    
                    return FVGEvent(
                        low=gap_high,
                        mid=(gap_high + gap_low) / 2,
                        high=gap_low,
                        size=size,
                        age=age,
                        filled=self._is_filled(gap_high, gap_low, current_price),
                        direction="bearish"  # FIXED: gap down = bearish
                    )
        
        return None
    
    def _is_filled(
        self,
        fvg_low: float,
        fvg_high: float,
        current_price: float
    ) -> bool:
        """Check if FVG has been filled."""
        # FVG is filled if price returns into the gap zone
        return fvg_low <= current_price <= fvg_high
    
    def calculate_fvg_strength(
        self,
        fvg: FVGEvent
    ) -> float:
        """Calculate FVG strength (0.0 to 1.0)."""
        strength = 0.5
        
        # Size factor
        strength += min(fvg.size * 5, 0.3)
        
        # Age factor (more recent = stronger)
        if fvg.age <= 2:
            strength += 0.2
        elif fvg.age <= 5:
            strength += 0.1
        
        # Not filled = stronger
        if not fvg.filled:
            strength += 0.1
        
        return min(strength, 1.0)
    
    def create_feature_breakdown(
        self,
        fvg: Optional[FVGEvent]
    ) -> FeatureBreakdown:
        """Create FeatureBreakdown from FVG event."""
        if fvg is None:
            return FeatureBreakdown(
                present=False,
                strength=0.0,
                reliability=0.0,
            )
        
        strength = self.calculate_fvg_strength(fvg)
        
        return FeatureBreakdown(
            present=True,
            strength=strength,
            age=fvg.age,
            filled=fvg.filled,
            reliability=min(strength * 1.2, 1.0),
            details=fvg.to_dict(),
        )


# FVG Module End