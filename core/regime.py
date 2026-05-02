"""
Regime Engine - Market Regime Detection.

This module detects market regime (trend, range, volatile)
for regime-adaptive scoring.

NOTE: Does NOT filter signals - only adjusts scores.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from core.signal_engine import RegimeType, MarketPhase, SessionType
from config import feature_flags as ff
from config.settings import SESSION_TIMES


@dataclass
class RegimeState:
    """Current regime state."""
    
    regime: RegimeType = RegimeType.RANGE
    phase: MarketPhase = MarketPhase.UNKNOWN
    strength: float = 0.0  # Regime strength (0.0 to 1.0)
    confidence: float = 0.0  # Detection confidence
    
    # Additional metrics
    trend_direction: str = ""  # "up", "down", ""
    trend_bars: int = 0         # Bars in current trend
    range_bounds: Tuple[float, float] = (0.0, 0.0)
    volatility: float = 0.0   # Current volatility


class RegimeEngine:
    """Engine for detecting market regime."""
    
    def __init__(self):
        self.enabled = ff.ENABLE_REGIME
        
        # Parameters
        self.trend_threshold = 0.5   # ATR multiplier for trend
        self.range_threshold = 0.3   # ATR for consolidation
        self.volume_threshold = 1.5  # Volume spike threshold
        
        # Session weights
        self.session_boosts = {
            SessionType.LONDON: 0.1,
            SessionType.NEW_YORK: 0.1,
            SessionType.TOKYO: -0.05,
            SessionType.SYDNEY: -0.05,
        }
    
    def detect_regime(
        self,
        prices: List[float],
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: Optional[List[float]] = None
    ) -> RegimeState:
        """Detect current market regime.
        
        Args:
            prices: Close prices (most recent last)
            highs: High prices
            lows: Low prices
            closes: Close prices
            volumes: Optional volume data
            
        Returns:
            RegimeState
        """
        if not self.enabled or len(prices) < 20:
            return RegimeState()
        
        state = RegimeState()
        
        # Calculate ATR for regime detection
        atr = self._calculate_atr(highs, lows, closes)
        current_price = prices[-1]
        
        # Calculate volatility
        state.volatility = atr / current_price if current_price > 0 else 0
        
        # Detect trend
        trend_detected, direction, bars = self._detect_trend(
            closes, atr
        )
        
        # Detect range
        range_bounds = self._detect_range(
            prices, atr
        )
        
        # Make regime decision
        if trend_detected:
            state.regime = RegimeType.TREND_UP if direction == "up" else RegimeType.TREND_DOWN
            state.trend_direction = direction
            state.trend_bars = bars
            state.strength = min(bars / 20.0, 1.0)
            state.range_bounds = (0.0, 0.0)
        elif range_bounds != (0.0, 0.0):
            state.regime = RegimeType.RANGE
            state.range_bounds = range_bounds
            state.strength = 0.7
        elif state.volatility > 0.01:  # High volatility
            state.regime = RegimeType.VOLATILE
            state.strength = 0.8
        else:
            state.regime = RegimeType.LOW_VOLATILITY
            state.strength = 0.3
        
        state.confidence = 0.7
        
        return state
    
    def _calculate_atr(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: int = 14
    ) -> float:
        """Calculate Average True Range."""
        if len(highs) < period + 1:
            return abs(highs[-1] - lows[-1]) if highs and lows else 0.001
        
        true_ranges = []
        for i in range(1, min(period + 1, len(highs))):
            high = highs[-i]
            low = lows[-i]
            prev_close = closes[-i - 1] if i < len(closes) else closes[-i]
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        return sum(true_ranges) / len(true_ranges) if true_ranges else 0.001
    
    def _detect_trend(
        self,
        closes: List[float],
        atr: float,
        lookback: int = 20
    ) -> Tuple[bool, str, int]:
        """Detect if market is in a trend.
        
        Returns:
            Tuple of (trend_detected, direction, bars_in_trend)
        """
        if len(closes) < lookback + 5:
            return False, "", 0
        
        # Check for higher highs / lower lows
        recent = closes[-lookback:]
        
        higher_highs = 0
        lower_lows = 0
        
        for i in range(1, len(recent) - 1):
            if recent[i] > recent[i-1] and recent[i] > recent[i+1]:
                higher_highs += 1
            elif recent[i] < recent[i-1] and recent[i] < recent[i+1]:
                lower_lows += 1
        
        price_change = closes[-1] - closes[-lookback]
        threshold = atr * self.trend_threshold
        
        if price_change > threshold:
            return True, "up", higher_highs + lower_lows
        elif price_change < -threshold:
            return True, "down", higher_highs + lower_lows
        
        return False, "", 0
    
    def _detect_range(
        self,
        prices: List[float],
        atr: float,
        lookback: int = 20
    ) -> Tuple[float, float]:
        """Detect if market is in a range.
        
        Returns:
            Tuple of (low, high) or (0, 0) if not ranging
        """
        if len(prices) < lookback:
            return (0.0, 0.0)
        
        recent = prices[-lookback:]
        max_price = max(recent)
        min_price = min(recent)
        
        range_size = max_price - min_price
        
        if range_size < atr * self.range_threshold * 3:
            return (min_price, max_price)
        
        return (0.0, 0.0)
    
    def get_regime_score_adjustment(
        self,
        regime: RegimeType,
        direction: str
    ) -> float:
        """Get score adjustment for regime.
        
        Args:
            regime: Current regime
            direction: Trade direction
            
        Returns:
            Score adjustment (+ is positive, - is negative)
        """
        if regime == RegimeType.TREND_UP:
            return 0.15 if direction == "long" else -0.1
        elif regime == RegimeType.TREND_DOWN:
            return 0.15 if direction == "short" else -0.1
        elif regime == RegimeType.RANGE:
            return -0.05  # Slight penalty in ranges
        elif regime == RegimeType.VOLATILE:
            return -0.1  # Penalty in volatile
        elif regime == RegimeType.LOW_VOLATILITY:
            return 0.05  # Slight boost in low vol
        
        return 0.0
    
    def get_current_session(
        self,
        hour: int
    ) -> SessionType:
        """Get current trading session based on hour (UTC).
        
        Args:
            hour: Hour of day (UTC)
            
        Returns:
            SessionType
        """
        for session, (start, end) in SESSION_TIMES.items():
            if start <= hour < end:
                return SessionType(session)
        
        return SessionType.OFF_SESSION
    
    def get_session_adjustment(
        self,
        session: SessionType
    ) -> float:
        """Get score adjustment for session.
        
        Args:
            session: Current session
            
        Returns:
            Score adjustment
        """
        return self.session_boosts.get(session, 0.0)
    
    def detect_phase(
        self,
        volumes: List[float],
        prices: List[float],
        regime: RegimeType
    ) -> MarketPhase:
        """Detect market phase (accumulation, manipulation, distribution).
        
        Args:
            volumes: Volume data
            prices: Price data
            regime: Current regime
            
        Returns:
            MarketPhase
        """
        if len(volumes) < 20 or len(prices) < 20:
            return MarketPhase.UNKNOWN
        
        # Simple phase detection based on volume/price relationship
        recent_vol = volumes[-10:]
        avg_volume = sum(volumes[-20:-10]) / 10
        
        price_change = prices[-1] - prices[-10]
        vol_spike = sum(recent_vol) / (avg_volume * 10) if avg_volume > 0 else 1.0
        
        if vol_spike > 1.5:
            if price_change > 0:
                return MarketPhase.DISTRIBUTION
            else:
                return MarketPhase.ACCUMULATION
        elif vol_spike < 0.7:
            return MarketPhase.MANIPULATION
        
        # Default based on regime
        if "trend" in regime.value:
            return MarketPhase.MANIPULATION
        
        return MarketPhase.CONSOLIDATION


# Regime Engine End