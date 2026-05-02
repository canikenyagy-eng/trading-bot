"""
SMC Liquidity Module - Liquidity Pool Detection.

Liquidity pools are areas where large orders accumulate,
often serving as stop loss hunting zones.
"""

from typing import List, Optional, Dict
from dataclasses import dataclass

from core.signal_engine import FeatureBreakdown
from config import feature_flags as ff


@dataclass
class LiquidityPool:
    """Liquidity pool."""
    
    # Pool level
    level: float = 0.0
    
    # Properties
    strength: float = 0.0
    pool_type: str = ""  # "swing_high", "swing_low", "range_high", "range_low"
    age: int = 0
    
    # Direction
    direction: str = ""  # "buy_side" or "sell_side"
    
    # Stops caught
    stop_estimate: float = 0.0  # Estimated stops caught
    
    def to_dict(self):
        return {
            "level": self.level,
            "strength": self.strength,
            "pool_type": self.pool_type,
            "age": self.age,
            "direction": self.direction,
            "stop_estimate": self.stop_estimate,
        }


class LiquidityDetector:
    """Detector for Liquidity Pools."""
    
    def __init__(self):
        self.enabled = ff.ENABLE_LIQUIDITY
        
        # Parameters
        self.lookback = 50
        self.consolidation_bars = 5
    
    def detect_swing_highs(
        self,
        highs: List[float],
        lookback: int = 20
    ) -> List[LiquidityPool]:
        """Find swing high liquidity pools."""
        pools = []
        
        if len(highs) < 5:
            return pools
        
        for i in range(2, len(highs) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2]:
                if highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                    strength = self._calculate_pool_strength(highs[i], highs)
                    
                    pools.append(LiquidityPool(
                        level=highs[i],
                        strength=strength,
                        pool_type="swing_high",
                        age=len(highs) - i - 1,
                        direction="sell_side",
                    ))
        
        return pools
    
    def detect_swing_lows(
        self,
        lows: List[float],
        lookback: int = 20
    ) -> List[LiquidityPool]:
        """Find swing low liquidity pools."""
        pools = []
        
        if len(lows) < 5:
            return pools
        
        for i in range(2, len(lows) - 2):
            if lows[i] < lows[i-1] and lows[i] < lows[i-2]:
                if lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                    strength = self._calculate_pool_strength(lows[i], lows)
                    
                    pools.append(LiquidityPool(
                        level=lows[i],
                        strength=strength,
                        pool_type="swing_low",
                        age=len(lows) - i - 1,
                        direction="buy_side",
                    ))
        
        return pools
    
    def detect_range_zones(
        self,
        prices: List[float],
        atr: float
    ) -> Dict[str, float]:
        """Detect range high/low liquidity zones."""
        if len(prices) < 10:
            return {}
        
        # Use recent range
        recent = prices[-20:]
        
        if not recent:
            return {}
        
        max_p = max(recent)
        min_p = min(recent)
        
        # Check if range is tight
        range_size = max_p - min_p
        
        if range_size < atr * 2:
            return {
                "range_high": max_p,
                "range_low": min_p,
            }
        
        return {}
    
    def find_nearest_liquidity(
        self,
        current_price: float,
        pools: List[LiquidityPool],
        direction: str
    ) -> Optional[LiquidityPool]:
        """Find nearest liquidity to price."""
        if not pools:
            return None
        
        # Filter by direction
        relevant = [p for p in pools if p.direction == direction]
        
        if not relevant:
            return None
        
        # Find closest to current price
        if direction == "sell_side":
            below = [p for p in relevant if p.level > current_price]
            if below:
                return min(below, key=lambda p: p.level - current_price)
        else:
            above = [p for p in relevant if p.level < current_price]
            if above:
                return min(above, key=lambda p: current_price - p.level)
        
        return None
    
    def _calculate_pool_strength(
        self,
        level: float,
        prices: List[float]
    ) -> float:
        """Calculate liquidity pool strength."""
        if not prices:
            return 0.5
        
        # Check how many times price tested this level
        tests = 0
        for p in prices[-20:]:
            if abs(p - level) / level < 0.001:
                tests += 1
        
        strength = 0.5 + min(tests * 0.1, 0.4)
        
        return strength
    
    def create_feature_breakdown(
        self,
        pool: Optional[LiquidityPool]
    ) -> FeatureBreakdown:
        """Create FeatureBreakdown from liquidity pool."""
        if pool is None:
            return FeatureBreakdown(
                present=False,
                strength=0.0,
                reliability=0.0,
            )
        
        return FeatureBreakdown(
            present=True,
            strength=pool.strength,
            age=pool.age,
            reliability=min(pool.strength, 1.0),
            details=pool.to_dict(),
        )


# Liquidity Module End