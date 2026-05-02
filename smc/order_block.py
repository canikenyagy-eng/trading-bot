"""
SMC Order Block Module - Order Block Detection.

Order Blocks are areas where institutions have placed
large orders, often acting as reversal zones.
"""

from typing import List, Optional
from dataclasses import dataclass

from core.signal_engine import FeatureBreakdown
from config import feature_flags as ff


@dataclass
class OrderBlockEvent:
    """Order Block event."""
    
    # Block boundaries
    low: float = 0.0
    high: float = 0.0
    mid: float = 0.0
    
    # Properties
    strength: float = 0.0
    touch_count: int = 0
    age: int = 0
    
    # Direction
    direction: str = ""  # "bullish" or "bearish"
    
    # Type
    is_continuation: bool = False  # True = continuation, False = reversal
    
    def to_dict(self):
        return {
            "low": self.low,
            "high": self.high,
            "mid": self.mid,
            "strength": self.strength,
            "touch_count": self.touch_count,
            "age": self.age,
            "direction": self.direction,
            "is_continuation": self.is_continuation,
        }


class OrderBlockDetector:
    """Detector for Order Blocks."""
    
    def __init__(self):
        self.enabled = ff.ENABLE_OB
        
        # Parameters
        self.min_touches = 1
        self.max_age = 20
        self.lookback = 50
    
    def detect_order_block(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        current_price: float,
        direction: str
    ) -> Optional[OrderBlockEvent]:
        """Detect Order Block.
        
        Args:
            highs: High prices
            lows: Low prices
            closes: Close prices
            current_price: Current market price
            direction: "long" or "short"
            
        Returns:
            OrderBlockEvent if OB detected, None otherwise
        """
        if not self.enabled or len(highs) < 10:
            return None
        
        # Look for large candle that established a move
        for i in range(len(closes) - 5, max(5, len(closes) - self.lookback), -1):
            body = abs(closes[i] - lows[i]) if direction == "long" else abs(highs[i] - closes[i])
            candle_size = highs[i] - lows[i]
            
            if candle_size == 0:
                continue
            
            body_ratio = body / candle_size
            
            # Large candle (over 70% body)
            if body_ratio > 0.7:
                # Check if this was the start of a move
                moves_after = self._count_direction_bars(closes[i:], direction)
                
                if moves_after >= 3:
                    # This might be an order block
                    ob_strength = self._calculate_ob_strength(
                        body_ratio, moves_after, candle_size, current_price
                    )
                    
                    if ob_strength > 0.3:
                        age = len(closes) - i - 1
                        touch_count = self._count_touches(
                            highs, lows, lows[i], highs[i], current_price
                        )
                        
                        is_cont = direction == "long" and closes[-1] > closes[i]
                        is_cont = is_cont or (direction == "short" and closes[-1] < closes[i])
                        
                        return OrderBlockEvent(
                            low=lows[i],
                            high=highs[i],
                            mid=(lows[i] + highs[i]) / 2,
                            strength=ob_strength,
                            touch_count=touch_count,
                            age=age,
                            direction="bullish" if direction == "long" else "bearish",
                            is_continuation=is_cont
                        )
        
        return None
    
    def _count_direction_bars(
        self,
        closes: List[float],
        direction: str
    ) -> int:
        """Count bars in a given direction."""
        if len(closes) < 2:
            return 0
        
        count = 0
        for i in range(1, len(closes)):
            if direction == "long" and closes[i] > closes[i-1]:
                count += 1
            elif direction == "short" and closes[i] < closes[i-1]:
                count += 1
        
        return count
    
    def _count_touches(
        self,
        highs: List[float],
        lows: List[float],
        zone_low: float,
        zone_high: float,
        current_price: float,
        tolerance: float = 0.0002
    ) -> int:
        """Count times price touched the zone."""
        count = 0
        
        for i in range(len(highs) - 10, len(highs)):
            if i >= len(highs) or i >= len(lows):
                continue
            
            high = highs[i]
            low = lows[i]
            
            # Check if candle overlapped with zone
            if (high >= zone_low - tolerance and low <= zone_high + tolerance):
                count += 1
        
        return count
    
    def _calculate_ob_strength(
        self,
        body_ratio: float,
        continuation_bars: int,
        candle_size: float,
        current_price: float
    ) -> float:
        """Calculate Order Block strength."""
        strength = 0.5
        
        # Stronger candle = stronger OB
        strength += body_ratio * 0.3
        
        # More continuation = stronger OB
        if continuation_bars >= 5:
            strength += 0.2
        elif continuation_bars >= 3:
            strength += 0.1
        
        return min(strength, 1.0)
    
    def create_feature_breakdown(
        self,
        ob: Optional[OrderBlockEvent]
    ) -> FeatureBreakdown:
        """Create FeatureBreakdown from OB event."""
        if ob is None:
            return FeatureBreakdown(
                present=False,
                strength=0.0,
                reliability=0.0,
            )
        
        return FeatureBreakdown(
            present=True,
            strength=ob.strength,
            age=ob.age,
            reliability=min(ob.strength + 0.1, 1.0),
            details=ob.to_dict(),
        )


# Order Block Module End