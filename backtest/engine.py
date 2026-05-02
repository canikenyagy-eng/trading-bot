"""
Backtest Engine - Historical Testing.

This module provides backtesting capabilities to validate
strategies before live deployment.

NOTE: This is for validation only, NOT for live trading.
"""

from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import json

from core.signal_engine import SignalEvaluation, Direction
from analytics.journaling import TradeJournal
from analytics.performance import PerformanceAnalyzer, PerformanceMetrics


@dataclass
class BacktestResult:
    """Backtest result."""
    
    # Overall metrics
    metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    
    # Trade log
    trades: List[Dict] = field(default_factory=list)
    
    # Additional stats
    equity_curve: List[float] = field(default_factory=list)
    
    # Per regime/stsession breakdown
    by_regime: Dict[str, PerformanceMetrics] = field(default_factory=dict)
    by_session: Dict[str, PerformanceMetrics] = field(default_factory=dict)


class BacktestEngine:
    """Engine for backtesting strategies."""
    
    def __init__(
        self, 
        initial_balance: float = 10000,
        risk_per_trade: float = 0.02
    ):
        self.initial_balance = initial_balance
        self.risk_per_trade = risk_per_trade
        
        self.commission = 0.0
        self.spread = 0.0
        self.slippage = 0
        
        # Results
        self.journal = TradeJournal()
        self.analyzer = PerformanceAnalyzer(self.journal)
        
        self._equity = [initial_balance]
        self._equity_curve = [initial_balance]
    
    def run_backtest(
        self,
        signals: List[SignalEvaluation],
        price_data: Dict[str, List[Dict]],
        regime_data: Optional[Dict[str, str]] = None
    ) -> BacktestResult:
        """Run backtest on signals.
        
        Args:
            signals: List of signals to test
            price_data: Historical price data by symbol
            regime_data: Optional regime by time
            
        Returns:
            BacktestResult
        """
        result = BacktestResult()
        
        for signal in signals:
            # Simulate trade
            trade = self._simulate_trade(signal, price_data.get(signal.symbol, []))
            
            if trade:
                result.trades.append(trade)
                
                # Record outcome
                self.journal.record_outcome(
                    signal.signal_id,
                    signal.symbol,
                    signal.direction.value,
                    signal.entry,
                    trade["exit"],
                    trade["result"],
                    trade["rr"]
                )
                
                # Update equity
                self._update_equity(trade["rr"])
        
        # Calculate final metrics
        result.metrics = self.analyzer.calculate_metrics()
        result.equity_curve = self._equity_curve
        
        return result
    
    def _simulate_trade(
        self,
        signal: SignalEvaluation,
        prices: List[Dict]
    ) -> Optional[Dict]:
        """Simulate a single trade."""
        if not signal.is_accepted or not signal.entry or not signal.sl:
            return None
        
        direction = signal.direction
        entry = signal.entry
        sl = signal.sl
        
        # Add spread and slippage
        entry_adjusted = entry + self.spread + self.slippage
        sl_adjusted = sl - self.spread - self.slippage
        
        # Find TP/SL hits
        tp_hit = None
        sl_hit = False
        
        for i, bar in enumerate(prices):
            high = bar.get("high", 0)
            low = bar.get("low", 0)
            close = bar.get("close", 0)
            
            if direction == Direction.LONG:
                # Check SL first
                if low <= sl_adjusted:
                    sl_hit = True
                    exit_price = sl_adjusted
                    break
                
                # Check each TP
                for tp in signal.tp_levels:
                    if high >= tp:
                        tp_hit = tp
                        break
                
                if tp_hit or sl_hit:
                    break
            
            else:  # SHORT
                if high >= sl_adjusted:
                    sl_hit = True
                    exit_price = sl_adjusted
                    break
                
                for tp in signal.tp_levels:
                    if low <= tp:
                        tp_hit = tp
                        break
                
                if tp_hit or sl_hit:
                    break
        
        if not tp_hit and not sl_hit:
            # Trade still open - use last price
            if prices:
                close = prices[-1].get("close", entry)
                
                if direction == Direction.LONG:
                    rr = (close - entry_adjusted) / (sl_adjusted - entry)
                else:
                    rr = (entry_adjusted - close) / (entry - sl_adjusted)
                
                return {
                    "signal_id": signal.signal_id,
                    "entry": entry_adjusted,
                    "exit": exit_price,
                    "result": "open",
                    "rr": rr,
                }
            
            return None
        
        # Calculate R
        if tp_hit:
            exit_price = tp_hit
            result = "tp"
            
            if direction == Direction.LONG:
                rr = (tp_hit - entry_adjusted) / (sl_adjusted - entry)
            else:
                rr = (entry_adjusted - tp_hit) / (entry - sl_adjusted)
        else:
            exit_price = sl_adjusted
            result = "sl"
            rr = -1.0
        
        # Deduct commission
        rr -= self.commission / (sl_adjusted - entry) if (sl_adjusted - entry) > 0 else 0
        
        return {
            "signal_id": signal.signal_id,
            "entry": entry_adjusted,
            "exit": exit_price,
            "result": result,
            "rr": rr,
        }
    
    def _update_equity(self, rr: float) -> None:
        """Update equity curve."""
        risk_amount = self._equity[-1] * self.risk_per_trade
        new_equity = self._equity[-1] + risk_amount * rr
        
        self._equity.append(new_equity)
        self._equity_curve.append(new_equity)
    
    def export_results(self, filepath: str) -> None:
        """Export backtest results."""
        results = {
            "metrics": self.analyzer.calculate_metrics().to_dict(),
            "trades": self.journal.outcomes,
            "equity_curve": self._equity_curve,
        }
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)


# Backtest Module End