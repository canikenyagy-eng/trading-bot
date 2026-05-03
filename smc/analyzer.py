"""
SMC Analyzer - Unified Smart Money Concepts Analyzer.

This module analyzes all SMC features: FVG, Order Blocks, Liquidity,
Structure, BOS, CHoCH, and MITIGATION zones.

CRITICAL: Analysis only - no auto-trading.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from core.signal_engine import FeatureBreakdown
from config import feature_flags as ff

# Import SMC modules
from smc.fvg import FVGDetector, FVGEvent
from smc.order_block import OrderBlockDetector, OrderBlockEvent
from smc.liquidity import LiquidityDetector, LiquidityPool


@dataclass
class SMCEvent:
    """Combined SMC event."""
    fvg: Optional[FVGEvent] = None
    order_block: Optional[OrderBlockEvent] = None
    liquidity_pool: Optional[LiquidityPool] = None
    
    # Combined strength
    combined_strength: float = 0.0
    
    # Direction bias
    direction_bias: str = ""  # "bullish", "bearish", "neutral"
    
    @property
    def has_features(self) -> bool:
        return bool(self.fvg or self.order_block or self.liquidity_pool)


class SMCAnalyzer:
    """Unified SMC analyzer.
    
    Combines all SMC feature detection into a single interface.
    """
    
    def __init__(self):
        self.fvg_detector = FVGDetector()
        self.ob_detector = OrderBlockDetector()
        self.liquidity_detector = LiquidityDetector()
        
        # Feature flags
        self.enable_fvg = ff.ENABLE_FVG
        self.enable_ob = ff.ENABLE_OB
        self.enable_liquidity = ff.ENABLE_LIQUIDITY
    
    def analyze(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        current_price: float,
        direction: str  # "long" or "short"
    ) -> SMCEvent:
        """Analyze all SMC features.
        
        Args:
            highs: High prices
            lows: Low prices
            closes: Close prices
            current_price: Current market price
            direction: Trade direction ("long" or "short")
            
        Returns:
            SMCEvent with all detected features
        """
        event = SMCEvent()
        
        # Map direction to FVG direction
        fvg_direction = "bullish" if direction == "long" else "bearish"
        
        # Detect FVG
        if self.enable_fvg:
            fvg = self.fvg_detector.detect_fvg(
                highs, lows, closes, current_price
            )
            # Filter FVG by trade direction
            if fvg and fvg.direction == fvg_direction:
                event.fvg = fvg
        
        # Detect Order Block
        if self.enable_ob:
            ob = self.ob_detector.detect_order_block(
                highs, lows, closes, current_price, direction
            )
            event.order_block = ob
        
        # Detect Liquidity
        if self.enable_liquidity:
            pools = self.liquidity_detector.detect_swing_highs(highs)
            pools.extend(self.liquidity_detector.detect_swing_lows(lows))
            
            # Find relevant pool
            pool_dir = "sell_side" if direction == "long" else "buy_side"
            pool = self.liquidity_detector.find_nearest_liquidity(
                current_price, pools, pool_dir
            )
            event.liquidity_pool = pool
        
        # Calculate combined strength
        event.combined_strength = self._calculate_combined_strength(event)
        
        # Determine direction bias
        event.direction_bias = self._determine_direction_bias(event, direction)
        
        return event
    
    def _calculate_combined_strength(self, event: SMCEvent) -> float:
        """Calculate combined feature strength."""
        strength = 0.0
        count = 0
        
        if event.fvg:
            strength += self.fvg_detector.calculate_fvg_strength(event.fvg)
            count += 1
        
        if event.order_block:
            strength += event.order_block.strength
            count += 1
        
        if event.liquidity_pool:
            strength += event.liquidity_pool.strength
            count += 1
        
        if count == 0:
            return 0.0
        
        return strength / count
    
    def _determine_direction_bias(
        self,
        event: SMCEvent,
        trade_direction: str
    ) -> str:
        """Determine overall direction bias from features."""
        bullish_score = 0
        bearish_score = 0
        
        # FVG contribution
        if event.fvg:
            if event.fvg.direction == "bullish":
                bullish_score += 1
            elif event.fvg.direction == "bearish":
                bearish_score += 1
        
        # Order block contribution
        if event.order_block:
            if event.order_block.direction == "bullish":
                bullish_score += 1
            elif event.order_block.direction == "bearish":
                bearish_score += 1
        
        # Determine bias
        if bullish_score > bearish_score:
            return "bullish"
        elif bearish_score > bullish_score:
            return "bearish"
        
        return "neutral"
    
    def create_feature_breakdowns(
        self,
        event: SMCEvent
    ) -> Dict[str, FeatureBreakdown]:
        """Create FeatureBreakdowns for each feature."""
        breakdowns = {}
        
        if event.fvg:
            breakdowns["fvg"] = self.fvg_detector.create_feature_breakdown(event.fvg)
        
        if event.order_block:
            breakdowns["order_block"] = self.ob_detector.create_feature_breakdown(
                event.order_block
            )
        
        if event.liquidity_pool:
            breakdowns["liquidity"] = self.liquidity_detector.create_feature_breakdown(
                event.liquidity_pool
            )
        
        return breakdowns
    
    def get_liquidity_context(
        self,
        highs: List[float],
        lows: List[float],
        current_price: float,
        direction: str
    ) -> str:
        """Get liquidity context description."""
        if not self.enable_liquidity:
            return "liquidity_detection_disabled"
        
        pools = []
        pools.extend(self.liquidity_detector.detect_swing_highs(highs))
        pools.extend(self.liquidity_detector.detect_swing_lows(lows))
        
        if not pools:
            return "no_liquidity_pools_found"
        
        # Find nearest pools
        pool_dir = "sell_side" if direction == "long" else "buy_side"
        above_pool = self.liquidity_detector.find_nearest_liquidity(
            current_price, pools, "sell_side"
        )
        below_pool = self.liquidity_detector.find_nearest_liquidity(
            current_price, pools, "buy_side"
        )
        
        context_parts = []
        
        if above_pool:
            dist_pips = (above_pool.level - current_price) * 10000
            context_parts.append(f"{dist_pips:.0f}p above")
        
        if below_pool:
            dist_pips = (current_price - below_pool.level) * 10000
            context_parts.append(f"{dist_pips:.0f}p below")
        
        if not context_parts:
            return "liquidity_at_current_price"
        
        return ", ".join(context_parts)


# SMC Analyzer End