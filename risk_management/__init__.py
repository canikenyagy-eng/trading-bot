"""Risk Management Module."""

import time
from dataclasses import dataclass, field
from typing import Dict
import logging

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Open position."""
    symbol: str
    direction: str
    quantity: int
    entry_price: float
    current_price: float
    unrealized_pnl: float = 0.0


@dataclass
class DailyStats:
    """Daily trading stats."""
    trades: int = 0
    wins: int = 0
    losses: int = 0
    volume: float = 0.0
    pnl: float = 0.0
    start_time: float = field(default_factory=time.time)


class RiskManager:
    """Risk management."""
    
    def __init__(self, config: dict):
        self.config = config
        self.positions: Dict[str, Position] = {}
        self.daily = DailyStats()
        self._last_reset = time.strftime("%Y%m%d")
    
    def check_position_size(self, symbol: str, quantity: int) -> bool:
        """Check position size limits."""
        max_size = self.config["risk"]["max_position_size"]
        
        current = self.positions.get(symbol, Position("", "", 0, 0, 0))
        
        if current.quantity + quantity > max_size:
            logger.warning(f"Position size exceeded for {symbol}")
            return False
        
        return True
    
    def check_daily_loss(self, pnl: float) -> bool:
        """Check daily loss limit."""
        max_loss = self.config["risk"]["max_daily_loss"]
        
        if abs(self.daily.pnl) >= max_loss:
            logger.critical(f"Daily loss limit reached: {self.daily.pnl}")
            return False
        
        return True
    
    def check_stop_loss(self, position: Position) -> bool:
        """Check stop loss."""
        if position.direction == "LONG":
            pnl_pct = (position.current_price - position.entry_price) / position.entry_price
        else:
            pnl_pct = (position.entry_price - position.current_price) / position.entry_price
        
        stop_pct = self.config["risk"]["stop_loss_pct"]
        
        if pnl_pct <= -stop_pct:
            logger.warning(f"Stop hit: {pnl_pct:.1%}")
            return True
        
        return False
    
    def check_take_profit(self, position: Position) -> bool:
        """Check take profit."""
        if position.direction == "LONG":
            pnl_pct = (position.current_price - position.entry_price) / position.entry_price
        else:
            pnl_pct = (position.entry_price - position.current_price) / position.entry_price
        
        tp_pct = self.config["risk"]["take_profit_pct"]
        
        if pnl_pct >= tp_pct:
            logger.info(f"Take profit hit: {pnl_pct:.1%}")
            return True
        
        return False
    
    def open_position(
        self,
        symbol: str,
        direction: str,
        quantity: int,
        price: float
    ) -> Position:
        """Open position."""
        pos = Position(
            symbol=symbol,
            direction=direction,
            quantity=quantity,
            entry_price=price,
            current_price=price
        )
        
        self.positions[symbol] = pos
        self.daily.trades += 1
        self.daily.volume += quantity
        
        logger.info(f"Opened {direction} {quantity} {symbol} @ {price}")
        
        return pos
    
    def close_position(self, symbol: str, exit_price: float, pnl: float) -> bool:
        """Close position."""
        if symbol not in self.positions:
            return False
        
        pos = self.positions[symbol]
        pos.current_price = exit_price
        
        if pnl > 0:
            self.daily.wins += 1
        else:
            self.daily.losses += 1
        
        self.daily.pnl += pnl
        
        del self.positions[symbol]
        
        logger.info(f"Closed {symbol} @ {exit_price}, PnL: {pnl:.2f}")
        
        return True
    
    def get_exposure(self, symbol: str) -> float:
        """Get position exposure."""
        if symbol in self.positions:
            pos = self.positions[symbol]
            return pos.quantity * pos.current_price
        return 0.0
    
    def get_total_exposure(self) -> float:
        """Get total portfolio exposure."""
        return sum(self.get_exposure(s) for s in self.positions)
    
    def reset_daily(self):
        """Reset daily stats."""
        today = time.strftime("%Y%m%d")
        
        if today != self._last_reset:
            self.daily = DailyStats()
            self._last_reset = today
            
            logger.info("Daily stats reset")