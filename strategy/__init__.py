"""
Strategy Module - RSI + EMA Event-Driven Strategy.
"""

import asyncio
from collections import deque
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    """Trading signal."""
    symbol: str
    direction: str  # "LONG" or "SHORT" or "FLAT"
    price: float
    confidence: float
    reason: str


class Indicator:
    """Rolling indicators."""
    
    def __init__(self, config: dict):
        self.rsi_period = config["strategy"]["rsi_period"]
        self.ema_fast = config["strategy"]["ema_fast"]
        self.ema_slow = config["strategy"]["ema_slow"]
        
        self._closes = deque(maxlen=self.ema_slow + 10)
        self._rsi_gains = deque(maxlen=self.rsi_period)
        self._rsi_losses = deque(maxlen=self.rsi_period)
    
    def update(self, close: float) -> dict:
        """Update with new close, return indicators."""
        self._closes.append(close)
        
        if len(self._closes) < 2:
            return {"rsi": 50, "ema_fast": close, "ema_slow": close}
        
        price_change = close - self._closes[-2]
        
        if price_change > 0:
            self._rsi_gains.append(price_change)
            self._rsi_losses.append(0)
        else:
            self._rsi_gains.append(0)
            self._rsi_losses.append(abs(price_change))
        
        avg_gain = sum(self._rsi_gains) / self.rsi_period if len(self._rsi_gains) >= self.rsi_period else 0
        avg_loss = sum(self._rsi_losses) / self.rsi_period if len(self._rsi_losses) >= self.rsi_period else 0
        
        rs = avg_gain / avg_loss if avg_loss > 0 else 1
        rsi = 100 - (100 / (1 + rs)) if avg_loss > 0 else 50
        
        ema_fast = self._calculate_ema(self.ema_fast)
        ema_slow = self._calculate_ema(self.ema_slow)
        
        return {"rsi": rsi, "ema_fast": ema_fast, "ema_slow": ema_slow}
    
    def _calculate_ema(self, period: int) -> float:
        """Calculate EMA."""
        if len(self._closes) < period:
            return sum(self._closes) / len(self._closes)
        
        multiplier = 2 / (period + 1)
        ema = sum(self._closes[-period:]) / period
        
        for i in range(-period + 1, 0):
            ema = (self._closes[i] - ema) * multiplier + ema
        
        return ema


class Strategy:
    """RSI + EMA strategy."""
    
    def __init__(self, config: dict, data_feed):
        self.config = config
        self.data_feed = data_feed
        self.indicators = {}
        self._signals = deque(maxlen=10)
    
    def add_symbol(self, symbol: str):
        """Add symbol to track."""
        self.indicators[symbol] = Indicator(self.config)
        logger.info(f"Strategy tracking {symbol}")
    
    def on_tick(self, symbol: str, tick) -> Optional[Signal]:
        """Process tick and generate signal."""
        if not tick or not tick.last or tick.last == 0:
            return None
        
        if symbol not in self.indicators:
            return None
        
        ind = self.indicators[symbol]
        inds = ind.update(tick.last)
        
        signal = self._generate_signal(symbol, tick.last, inds)
        
        if signal:
            self._signals.append(signal)
        
        return signal
    
    def _generate_signal(self, symbol: str, price: float, inds: dict) -> Optional[Signal]:
        """Generate trading signal."""
        rsi = inds["rsi"]
        ema_fast = inds["ema_fast"]
        ema_slow = inds["ema_slow"]
        
        oversold = self.config["strategy"]["oversold"]
        overbought = self.config["strategy"]["overbought"]
        
        direction = "FLAT"
        reason = ""
        confidence = 0.5
        
        if rsi < oversold and ema_fast > ema_slow:
            direction = "LONG"
            reason = f"RSI={rsi:.0f}<{oversold}, EMA_fast>EMA_slow"
            confidence = (oversold - rsi) / oversold
        
        elif rsi > overbought and ema_fast < ema_slow:
            direction = "SHORT"
            reason = f"RSI={rsi:.0f}>{overbought}, EMA_fast<EMA_slow"
            confidence = (rsi - overbought) / (100 - overbought)
        
        if direction == "FLAT":
            return None
        
        return Signal(
            symbol=symbol,
            direction=direction,
            price=price,
            confidence=min(0.95, confidence),
            reason=reason
        )
    
    def get_pending(self, symbol: str) -> Optional[Signal]:
        """Get last signal for symbol."""
        for sig in reversed(self._signals):
            if sig.symbol == symbol:
                return sig
        return None