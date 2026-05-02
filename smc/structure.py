"""
SMC Structure Module - Market Structure Detection.

This module provides basic structure detection capabilities
(BOS/CHOCH) for the Smart Money Concepts system.

Structure detection provides the foundation for all SMC analysis.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from core.signal_engine import FeatureBreakdown
from config import feature_flags as ff


class StructureType(str, Enum):
    """Type of structure formation."""
    BOS = "bos"           # Break of Structure
    CH_OCH = "choch"      # Change of Character
    CONSOLIDATION = "consolidation"
    UNKNOWN = "unknown"


class DirectionBias(str, Enum):
    """Structure direction bias."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class StructurePoint:
    """A single structure point (high/low)."""
    
    index: int
    price: float
    type: str  # "high" or "low"
    broken: bool = False
    strength: float = 0.0


@dataclass
class StructureEvent:
    """A structure formation event."""
    
    type: StructureType
    direction: DirectionBias
    timestamp: Optional[str] = None
    
    # Prices
    trigger_price: float = 0.0
    breakout_price: float = 0.0
    
    # Quality
    strength: float = 0.0
    confirmation_bars: int = 0
    
    # Context
    liquidity_before: float = 0.0
    liquidity_after: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "direction": self.direction.value,
            "trigger_price": self.trigger_price,
            "breakout_price": self.breakout_price,
            "strength": self.strength,
            "confirmation_bars": self.confirmation_bars,
        }


class StructureDetector:
    """Detector for market structure (BOS/CHOCH)."""
    
    def __init__(self):
        self.enabled = ff.ENABLE_STRUCTURE
        
        # Parameters
        self.min_swing_size = 0.001  # Minimum swing size (0.1%)
        self.confirmation_bars = 2    # Bars to confirm BOS
        self.lookback = 100            # Bars to look back
    
    def find_structure_points(
        self,
        highs: List[float],
        lows: List[float],
        close: float
    ) -> Tuple[List[StructurePoint], List[StructurePoint]]:
        """Find swing highs and lows.
        
        Args:
            highs: High prices
            lows: Low prices
            close: Current close
            
        Returns:
            Tuple of (swing_highs, swing_lows)
        """
        swing_highs: List[StructurePoint] = []
        swing_lows: List[StructurePoint] = []
        
        if len(highs) < 5 or len(lows) < 5:
            return swing_highs, swing_lows
        
        # Find swing highs (5-bar pivot)
        for i in range(2, len(highs) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2]:
                if highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                    swing_highs.append(StructurePoint(
                        index=i,
                        price=highs[i],
                        type="high",
                        strength=1.0
                    ))
        
        # Find swing lows
        for i in range(2, len(lows) - 2):
            if lows[i] < lows[i-1] and lows[i] < lows[i-2]:
                if lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                    swing_lows.append(StructurePoint(
                        index=i,
                        price=lows[i],
                        type="low",
                        strength=1.0
                    ))
        
        return swing_highs, swing_lows
    
    def detect_bos(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        direction: str
    ) -> Optional[StructureEvent]:
        """Detect Break of Structure.
        
        Args:
            highs: High prices
            lows: Low prices
            closes: Close prices
            direction: "bullish" or "bearish"
            
        Returns:
            StructureEvent if BOS detected, None otherwise
        """
        if not self.enabled:
            return None
        
        swing_highs, swing_lows = self.find_structure_points(highs, lows, closes[-1])
        
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return None
        
        # Get most recent swing points
        if direction == "bullish":
            last_swing_low = swing_lows[-1]
            previous_swing_low = swing_lows[-2] if len(swing_lows) >= 2 else None
            
            if previous_swing_low is None:
                return None
            
            # Check if current price broke above last swing high
            last_swing_high = swing_highs[-1]
            
            if closes[-1] > last_swing_high.price:
                return StructureEvent(
                    type=StructureType.BOS,
                    direction=DirectionBias.BULLISH,
                    trigger_price=last_swing_low.price,
                    breakout_price=last_swing_high.price,
                    strength=self._calculate_strength(
                        last_swing_high.price,
                        last_swing_low.price,
                        last_swing_low.price
                    ),
                    confirmation_bars=self._count_confirmation_bars(closes, last_swing_high.price),
                )
        
        else:  # bearish
            last_swing_high = swing_highs[-1]
            previous_swing_high = swing_highs[-2] if len(swing_highs) >= 2 else None
            
            if previous_swing_high is None:
                return None
            
            last_swing_low = swing_lows[-1]
            
            if closes[-1] < last_swing_low.price:
                return StructureEvent(
                    type=StructureType.BOS,
                    direction=DirectionBias.BEARISH,
                    trigger_price=last_swing_high.price,
                    breakout_price=last_swing_low.price,
                    strength=self._calculate_strength(
                        last_swing_high.price,
                        last_swing_low.price,
                        last_swing_high.price
                    ),
                    confirmation_bars=self._count_confirmation_bars(closes, last_swing_low.price, is_bullish=False),
                )
        
        return None
    
    def detect_choch(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float]
    ) -> Optional[StructureEvent]:
        """Detect Change of Character (CHOCH).
        
        Args:
            highs: High prices
            lows: Low prices
            closes: Close prices
            
        Returns:
            StructureEvent if CHOCH detected, None otherwise
        """
        if not self.enabled:
            return None
        
        # Look for structure flip
        swing_highs, swing_lows = self.find_structure_points(highs, lows, closes[-1])
        
        if len(swing_highs) < 3 or len(swing_lows) < 3:
            return None
        
        # Get last few swing points
        recent_highs = swing_highs[-3:]
        recent_lows = swing_lows[-3:]
        
        # Check for trend change
        if len(recent_highs) >= 2 and len(recent_lows) >= 2:
            # Was: higher highs + higher lows (uptrend)
            # Now: lower highs + lower lows (downtrend)
            
            was_uptrend = (
                recent_highs[-2].price > recent_highs[-3].price and
                recent_lows[-2].price > recent_lows[-3].price
            )
            
            now_downtrend = (
                recent_highs[-1].price < recent_highs[-2].price and
                recent_lows[-1].price < recent_lows[-2].price
            )
            
            if was_uptrend and now_downtrend:
                return StructureEvent(
                    type=StructureType.CH_OCH,
                    direction=DirectionBias.BEARISH,
                    strength=0.8,
                )
            
            # Vice versa
            was_downtrend = (
                recent_highs[-2].price < recent_highs[-3].price and
                recent_lows[-2].price < recent_lows[-3].price
            )
            
            now_uptrend = (
                recent_highs[-1].price > recent_highs[-2].price and
                recent_lows[-1].price > recent_lows[-2].price
            )
            
            if was_downtrend and now_uptrend:
                return StructureEvent(
                    type=StructureType.CH_OCH,
                    direction=DirectionBias.BULLISH,
                    strength=0.8,
                )
        
        return None
    
    def _calculate_strength(
        self,
        breakout: float,
        trigger: float,
        reference: float
    ) -> float:
        """Calculate structure strength."""
        if reference == 0:
            return 0.5
        
        size = abs(breakout - trigger)
        distance = abs(breakout - reference)
        
        if distance == 0:
            return 0.5
        
        strength = size / distance
        return min(strength * 2, 1.0)
    
    def _count_confirmation_bars(
        self,
        closes: List[float],
        level: float,
        is_bullish: bool = True
    ) -> int:
        """Count bars that closed beyond level."""
        count = 0
        
        for close in closes[-self.confirmation_bars:]:
            if is_bullish and close > level:
                count += 1
            elif not is_bullish and close < level:
                count += 1
        
        return count
    
    def create_feature_breakdown(
        self,
        event: Optional[StructureEvent]
    ) -> FeatureBreakdown:
        """Create FeatureBreakdown from structure event.
        
        Args:
            event: StructureEvent or None
            
        Returns:
            FeatureBreakdown
        """
        if event is None:
            return FeatureBreakdown(
                present=False,
                strength=0.0,
                reliability=0.0,
            )
        
        return FeatureBreakdown(
            present=True,
            strength=event.strength,
            age=event.confirmation_bars,
            filled=False,
            reliability=min(event.strength + 0.2, 1.0),
            details=event.to_dict(),
        )


# Structure Module End