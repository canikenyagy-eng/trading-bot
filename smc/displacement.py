"""
Displacement Engine - Impulse/Displacement Strength Detection.

Measures the strength of price moves relative to ATR to identify
valid BOS (Break of Structure) and impulse moves.

CRITICAL: Analysis only - no auto-trading.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from config import feature_flags as ff


@dataclass
class DisplacementEvent:
    """Displacement event."""
    
    # Strength metrics
    displacement: float = 0.0  # Move size in ATRs
    displacement_pct: float = 0.0  # Move size in percent
    
    # Context
    context: str = ""  # "pre_bos", "post_bos", "impulse", "correction"
    direction: str = ""  # "bullish", "bearish"
    
    # Quality metrics
    continuity: float = 0.0  # How many consecutive bars in direction
    acceleration: float = 0.0  # Is move accelerating?
    deceleration: float = 0.0  # Is move losing momentum?
    
    # Reliability
    reliability: float = 0.5
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "displacement": self.displacement,
            "displacement_pct": self.displacement_pct,
            "context": self.context,
            "direction": self.direction,
            "continuity": self.continuity,
            "acceleration": self.acceleration,
            "deceleration": self.deceleration,
            "reliability": self.reliability,
        }


class DisplacementEngine:
    """Displacement detection engine."""
    
    def __init__(self):
        self.enabled = ff.ENABLE_DISPLACEMENT
        
        # Parameters
        self.min_displacement = 0.5  # Minimum 0.5 ATR to be valid
        self.strong_displacement = 1.5  # 1.5+ ATR = strong
        self.lookback = 20  # Bars to look for structure
    
    def calculate_atr(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: int = 14
    ) -> float:
        """Calculate ATR (Average True Range)."""
        if len(highs) < period + 1:
            return self._estimate_atr(highs, lows)
        
        # True Range calculation
        tr = []
        for i in range(1, min(period + 1, len(highs))):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i - 1])
            low_close = abs(lows[i] - closes[i - 1])
            
            tr.append(max(high_low, high_close, low_close))
        
        if not tr:
            return self._estimate_atr(highs, lows)
        
        return sum(tr) / len(tr)
    
    def _estimate_atr(self, highs: List[float], lows: List[float]) -> float:
        """Estimate ATR from high-low range."""
        if len(highs) < 2:
            return 0.0001
        
        ranges = [highs[i] - lows[i] for i in range(len(highs))]
        return sum(ranges) / len(ranges) / 2
    
    def calculate_displacement(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        current_price: float,
        direction: str,  # "bullish" or "bearish"
        atr: Optional[float] = None
    ) -> DisplacementEvent:
        """Calculate displacement from last major move.
        
        Args:
            highs: High prices
            lows: Low prices
            closes: Close prices
            current_price: Current market price
            direction: Trade direction
            atr: Optional ATR (calculated if not provided)
            
        Returns:
            DisplacementEvent with strength metrics
        """
        if not self.enabled:
            return DisplacementEvent()
        
        # Calculate ATR
        if atr is None:
            atr = self.calculate_atr(highs, lows, closes)
        
        if atr == 0:
            atr = self._estimate_atr(highs, lows)
        
        # Find last significant move
        move_start = self._find_move_start(closes, direction)
        
        if move_start is None:
            return DisplacementEvent()
        
        # Calculate move
        if direction == "bullish":
            move = current_price - closes[move_start]
        else:
            move = closes[move_start] - current_price
        
        if move <= 0:
            return DisplacementEvent()
        
        # Displacement in ATRs
        displacement = move / atr
        displacement_pct = move / closes[move_start]
        
        # Calculate continuity (consecutive bars in direction)
        continuity = self._calculate_continuity(closes, direction)
        
        # Calculate acceleration/deceleration
        acceleration, deceleration = self._calculate_momentum(
            highs, lows, closes, direction, move_start
        )
        
        # Determine context
        context = self._determine_context(
            displacement, continuity, acceleration
        )
        
        # Calculate reliability
        reliability = self._calculate_reliability(
            displacement, continuity, acceleration, deceleration
        )
        
        return DisplacementEvent(
            displacement=displacement,
            displacement_pct=displacement_pct,
            context=context,
            direction=direction,
            continuity=continuity,
            acceleration=acceleration,
            deceleration=deceleration,
            reliability=reliability
        )
    
    def _find_move_start(
        self,
        closes: List[str],
        direction: str
    ) -> Optional[int]:
        """Find start of major move."""
        if len(closes) < 5:
            return None
        
        # Look for trend change
        for i in range(len(closes) - 2, len(closes) - self.lookback, -1):
            if direction == "bullish":
                # Find first close that is significantly higher
                if closes[i] > closes[i - 1] * 1.002:  # 0.2% minimum
                    return i
            else:
                if closes[i] < closes[i - 1] * 0.998:
                    return i
        
        # Fallback to recent significant move
        return len(closes) - 5
    
    def _calculate_continuity(
        self,
        closes: List[float],
        direction: str,
        start: Optional[int] = None
    ) -> float:
        """Calculate how many consecutive bars in direction."""
        if start is None:
            start = max(0, len(closes) - 10)
        
        continuity = 0
        for i in range(start, len(closes) - 1):
            if direction == "bullish":
                if closes[i + 1] > closes[i]:
                    continuity += 1
                else:
                    break
            else:
                if closes[i + 1] < closes[i]:
                    continuity += 1
                else:
                    break
        
        return continuity
    
    def _calculate_momentum(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        direction: str,
        start: int
    ) -> tuple:
        """Calculate acceleration/deceleration."""
        if len(closes) - start < 5:
            return 0.0, 0.0
        
        # Split into halves
        first_half = closes[start:start + 3]
        second_half = closes[start + 3:min(start + 6, len(closes))]
        
        if len(first_half) < 2 or len(second_half) < 2:
            return 0.0, 0.0
        
        first_move = first_half[-1] - first_half[0]
        second_move = second_half[-1] - second_half[0]
        
        if first_move == 0:
            return 0.0, 0.0
        
        # Acceleration/deceleration as ratio
        ratio = second_move / first_move
        
        if ratio > 1.2:
            return min(ratio, 2.0), 0.0
        elif ratio < 0.8:
            return 0.0, min(1 / ratio, 2.0)
        
        return 0.0, 0.0
    
    def _determine_context(
        self,
        displacement: float,
        continuity: float,
        acceleration: float
    ) -> str:
        """Determine move context."""
        if displacement < self.min_displacement:
            return "consolidation"
        
        if continuity >= 4 and displacement >= self.strong_displacement:
            return "impulse"
        
        if acceleration > 0:
            return "accelerating"
        
        if displacement >= 1.0:
            return "post_bos"
        
        if displacement >= self.min_displacement:
            return "pre_bos"
        
        return "correction"
    
    def _calculate_reliability(
        self,
        displacement: float,
        continuity: float,
        acceleration: float,
        deceleration: float
    ) -> float:
        """Calculate reliability (0.0-1.0)."""
        reliability = 0.5
        
        # Displacement adds reliability
        if displacement >= self.strong_displacement:
            reliability += 0.3
        elif displacement >= 1.0:
            reliability += 0.2
        elif displacement >= self.min_displacement:
            reliability += 0.1
        
        # Continuity adds reliability
        reliability += min(continuity * 0.05, 0.2)
        
        # Acceleration adds, deceleration reduces
        if acceleration > 0:
            reliability += min(acceleration * 0.1, 0.1)
        elif deceleration > 0:
            reliability -= min(deceleration * 0.1, 0.2)
        
        return max(0.0, min(1.0, reliability))
    
    def normalize_displacement(
        self,
        displacement_event: DisplacementEvent
    ) -> float:
        """Normalize displacement to 0-1 scale."""
        if not displacement_event or displacement_event.displacement == 0:
            return 0.0
        
        # Strong displacement = high normalized value
        normalized = displacement_event.displacement / 3.0
        
        # Adjust for context
        if displacement_event.context == "impulse":
            normalized *= 1.2
        elif displacement_event.context == "correction":
            normalized *= 0.5
        
        return min(1.0, normalized)
    
    def is_strong_move(
        self,
        displacement_event: DisplacementEvent
    ) -> bool:
        """Check if this is a strong move (valid for trading)."""
        if not self.enabled:
            return True
        
        return (
            displacement_event.displacement >= self.min_displacement and
            displacement_event.context in ["impulse", "post_bos"] and
            displacement_event.deceleration < 0.3
        )


# Displacement Engine End