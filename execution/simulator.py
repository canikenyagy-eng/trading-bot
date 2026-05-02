"""
Execution Simulator - Trade Simulation Only.

CRITICAL: This module simulates trades for backtesting and validation.
NO live trading execution is performed.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from core.signal_engine import SignalEvaluation, Direction


class TradeState(str, Enum):
    """Trade state machine."""
    OPEN = "open"
    PARTIAL = "partial"    # Partial TP taken
    PROTECTED = "protected"  # Break-even reached
    CLOSED = "closed"


@dataclass
class SimulatedTrade:
    """Simulated trade for testing."""
    
    signal_id: str
    symbol: str
    direction: Direction
    
    # Entry
    entry_price: float = 0.0
    entry_time: str = ""
    
    # Levels
    sl_price: float = 0.0
    tp_levels: List[float] = []
    
    # State
    state: TradeState = TradeState.OPEN
    
    # Tracking
    tp_taken: List[Dict] = []  # Partial TPs taken
    current_rr: float = 0.0
    
    # Metrics
    max_r: float = 0.0
    min_r: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "signal_id": self.signal_id,
            "symbol": self.symbol,
            "direction": self.direction.value,
            "entry": self.entry_price,
            "sl": self.sl_price,
            "tp_levels": self.tp_levels,
            "state": self.state.value,
            "current_rr": self.current_rr,
            "max_r": self.max_r,
            "min_r": self.min_r,
        }


class TradeSimulator:
    """Simulator for trade management.
    
    CRITICAL: This is simulation only. NO live trading.
    """
    
    def __init__(self):
        self._trades: Dict[str, SimulatedTrade] = {}
        
        # Configuration
        self.partial_tp_enabled = True
        self.be_enabled = True
        self.trailing_enabled = True
    
    def open_trade(
        self,
        signal: SignalEvaluation
    ) -> SimulatedTrade:
        """Open a simulated trade."""
        if not signal.is_accepted:
            raise ValueError("Cannot open rejected signal")
        
        trade = SimulatedTrade(
            signal_id=signal.signal_id,
            symbol=signal.symbol,
            direction=signal.direction,
            entry_price=signal.entry,
            sl_price=signal.sl,
            tp_levels=signal.tp_levels.copy(),
        )
        
        self._trades[signal.signal_id] = trade
        
        return trade
    
    def update_trade(
        self,
        signal_id: str,
        current_price: float,
        high: float,
        low: float
    ) -> SimulatedTrade:
        """Update trade state with new price data."""
        if signal_id not in self._trades:
            raise ValueError(f"Trade {signal_id} not found")
        
        trade = self._trades[signal_id]
        
        # Skip if already closed
        if trade.state == TradeState.CLOSED:
            return trade
        
        # Calculate current R
        if trade.direction == Direction.LONG:
            rr = (current_price - trade.entry_price) / (trade.entry_price - trade.sl_price)
        else:
            rr = (trade.entry_price - current_price) / (trade.sl_price - trade.entry_price)
        
        trade.current_rr = rr
        
        # Track max/min R
        if rr > trade.max_r:
            trade.max_r = rr
        if rr < trade.min_r:
            trade.min_r = rr
        
        # Check TP levels
        if self.partial_tp_enabled:
            trade = self._check_partial_tp(trade, high, low)
        
        # Check BE
        if self.be_enabled and trade.state == TradeState.OPEN:
            if rr >= 1.0:
                trade.state = TradeState.PROTECTED
                trade.tp_taken.append({
                    "type": "be_move",
                    "rr": 1.0,
                })
        
        # Check SL
        if self._check_sl(trade, high, low):
            trade.state = TradeState.CLOSED
        
        return trade
    
    def _check_partial_tp(
        self,
        trade: SimulatedTrade,
        high: float,
        low: float
    ) -> SimulatedTrade:
        """Check partial TP levels."""
        if trade.state != TradeState.OPEN:
            return trade
        
        direction = trade.direction
        
        # 50% TP at 1R
        if 1.0 not in [t["rr"] for t in trade.tp_taken]:
            if direction == Direction.LONG and high >= trade.tp_levels[0]:
                trade.state = TradeState.PARTIAL
                trade.tp_taken.append({
                    "type": "partial",
                    "tp_level": trade.tp_levels[0],
                    "rr": 1.0,
                })
            elif direction == Direction.SHORT and low <= trade.tp_levels[0]:
                trade.state = TradeState.PARTIAL
                trade.tp_taken.append({
                    "type": "partial",
                    "tp_level": trade.tp_levels[0],
                    "rr": 1.0,
                })
        
        return trade
    
    def _check_sl(
        self,
        trade: SimulatedTrade,
        high: float,
        low: float
    ) -> bool:
        """Check if SL was hit."""
        direction = trade.direction
        
        if direction == Direction.LONG:
            return low <= trade.sl_price
        else:
            return high >= trade.sl_price
    
    def close_trade(
        self,
        signal_id: str,
        reason: str
    ) -> SimulatedTrade:
        """Manually close trade."""
        if signal_id not in self._trades:
            raise ValueError(f"Trade {signal_id} not found")
        
        trade = self._trades[signal_id]
        trade.state = TradeState.CLOSED
        
        return trade
    
    def get_trade(
        self,
        signal_id: str
    ) -> Optional[SimulatedTrade]:
        """Get trade by signal ID."""
        return self._trades.get(signal_id)
    
    def get_open_trades(self) -> List[SimulatedTrade]:
        """Get all open trades."""
        return [
            t for t in self._trades.values()
            if t.state != TradeState.CLOSED
        ]
    
    def get_closed_trades(self) -> List[SimulatedTrade]:
        """Get all closed trades."""
        return [
            t for t in self._trades.values()
            if t.state == TradeState.CLOSED
        ]
    
    def get_summary(self) -> Dict:
        """Get simulator summary."""
        closed = self.get_closed_trades()
        
        if not closed:
            return {
                "total_trades": 0,
                "open_trades": len(self.get_open_trades()),
                "avg_rr": 0.0,
            }
        
        wins = [t for t in closed if t.current_rr > 0]
        losses = [t for t in closed if t.current_rr < 0]
        
        return {
            "total_trades": len(closed),
            "open_trades": len(self.get_open_trades()),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": len(wins) / len(closed),
            "avg_rr": sum(t.current_rr for t in closed) / len(closed),
            "max_r": max(t.max_r for t in closed) if closed else 0,
            "min_r": min(t.min_r for t in closed) if closed else 0,
        }


# Simulator End