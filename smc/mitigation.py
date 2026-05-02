"""
SMC Mitigation Module - Mitigation Zone Detection.

Mitigation zones are areas where price has been rejected,
acting as potential reversal points.
"""

from typing import List, Optional
from dataclasses import dataclass

from core.signal_engine import FeatureBreakdown
from config import feature_flags as ff


@dataclass
class MitigationEvent:
    """Mitigation zone event."""
    
    # Zone
    low: float = 0.0
    high: float = 0.0
    mid: float = 0.0
    
    # Properties
    strength: float = 0.0
    rejection_count: int = 0
    age: int = 0
    
    # Direction
    direction: str = ""
    
    def to_dict(self):
        return {
            "low": self.low,
            "high": self.high,
            "mid": self.mid,
            "strength": self.strength,
            "rejection_count": self.rejection_count,
            "age": self.age,
            "direction": self.direction,
        }


class MitigationDetector:
    """Detector for Mitigation Zones."""
    
    def __init__(self):
        self.enabled = ff.ENABLE_MITIGATION
        
        # Parameters
        self.rejection_threshold = 0.0005  # Minimum rejection size
        self.min_rejections = 2
        self.max_age = 10
    
    def detect_mitigation(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        current_price: float
    ) -> Optional[MitigationEvent]:
        """Detect Mitigation Zone.
        
        Args:
            highs: High prices
            lows: Low prices
            closes: Close prices
            current_price: Current market price
            
        Returns:
            MitigationEvent if detected, None otherwise
        """
        if not self.enabled or len(highs) < 5:
            return None
        
        # Find rejection zones (areas with wicks)
        rejections: List[dict] = []
        
        for i in range(len(highs) - 1, max(2, len(highs) - self.max_age * 3), -1):
            high = highs[i]
            low = lows[i]
            close = closes[i]
            
            # Upper wick
            upper_wick = high - max(close, lows[i])
            # Lower wick
            lower_wick = min(close, highs[i]) - low
            
            total_range = high - low
            if total_range == 0:
                continue
            
            upper_ratio = upper_wick / total_range
            lower_ratio = lower_wick / total_range
            
            # Significant wick on either side
            if upper_ratio > 0.3 or lower_ratio > 0.3:
                # Determine direction
                direction = "bearish" if upper_ratio > lower_ratio else "bullish"
                
                # Calculate strength based on wick size
                wick_size = max(upper_wick, lower_wick)
                strength = min(wick_size / total_range, 1.0)
                
                rejections.append({
                    "index": i,
                    "low": low,
                    "high": high,
                    "direction": direction,
                    "strength": strength,
                })
        
        if len(rejections) < self.min_rejections:
            return None
        
        # Find overlapping rejections (same direction)
        bullish_rejections = [r for r in rejections if r["direction"] == "bullish"]
        bearish_rejections = [r for r in rejections if r["direction"] == "bearish"]
        
        if len(bullish_rejections) >= self.min_rejections:
            # Find common zone
            zone = self._find_common_zone(bullish_rejections)
            return self._create_mitigation_event(zone, current_price, "bullish")
        
        if len(bearish_rejections) >= self.min_rejections:
            zone = self._find_common_zone(bearish_rejections)
            return self._create_mitigation_event(zone, current_price, "bearish")
        
        return None
    
    def _find_common_zone(
        self,
        rejections: List[dict]
    ) -> dict:
        """Find common zone from multiple rejections."""
        if not rejections:
            return {"low": 0, "high": 0}
        
        lows = [r["low"] for r in rejections]
        highs = [r["high"] for r in rejections]
        
        # Use recent rejections
        recent = sorted(rejections, key=lambda x: x["index"])[:3]
        
        return {
            "low": min(r["low"] for r in recent),
            "high": max(r["high"] for r in recent),
            "rejection_count": len(recent),
            "strength": sum(r["strength"] for r in recent) / len(recent),
        }
    
    def _create_mitigation_event(
        self,
        zone: dict,
        current_price: float,
        direction: str
    ) -> MitigationEvent:
        """Create MitigationEvent from zone."""
        low = zone.get("low", 0)
        high = zone.get("high", 0)
        
        age = 5  # Estimated
        
        # Check if mitigated
        filled = False
        if direction == "bullish" and current_price > high:
            filled = True
        elif direction == "bearish" and current_price < low:
            filled = True
        
        return MitigationEvent(
            low=low,
            high=high,
            mid=(low + high) / 2,
            strength=zone.get("strength", 0.5),
            rejection_count=zone.get("rejection_count", 2),
            age=age,
            direction=direction,
        )
    
    def create_feature_breakdown(
        self,
        event: Optional[MitigationEvent]
    ) -> FeatureBreakdown:
        """Create FeatureBreakdown from mitigation event."""
        if event is None:
            return FeatureBreakdown(
                present=False,
                strength=0.0,
                reliability=0.0,
            )
        
        return FeatureBreakdown(
            present=True,
            strength=event.strength,
            age=event.age,
            filled=False,
            reliability=min(event.strength + 0.2, 1.0),
            details=event.to_dict(),
        )


# Mitigation Module End