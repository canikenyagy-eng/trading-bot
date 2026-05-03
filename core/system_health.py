"""
System Health Monitor - Real-Time System Performance Tracking.

Tracks system health metrics and detects degradation.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque


@dataclass
class SystemHealth:
    """Current system health metrics."""
    
    winrate_last_n: float = 0.5
    profit_factor: float = 1.0
    drawdown: float = 0.0
    signal_frequency: float = 0.0
    avg_r: float = 0.0
    signal_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "winrate_last_n": self.winrate_last_n,
            "profit_factor": self.profit_factor,
            "drawdown": self.drawdown,
            "signal_frequency": self.signal_frequency,
            "avg_r": self.avg_r,
            "signal_count": self.signal_count,
        }


class SystemHealthMonitor:
    """System health monitoring engine."""
    
    def __init__(self):
        # Window sizes
        self.winrate_window = 20
        self.perf_window = 50
        
        # Rolling buffers
        self.recent_results: deque = deque(maxlen=self.perf_window)
        self.recent_rr: deque = deque(maxlen=self.perf_window)
        self.recent_signals: deque = deque(maxlen=100)
        
        # Baseline (for comparison)
        self.baseline_winrate = 0.55
        self.baseline_pf = 1.3
        self.baseline_avg_r = 0.2
        
        # Thresholds
        self.winrate_drop_threshold = 0.10  # 10%
        self.pf_drop_threshold = 0.30  # 30%
        self.drawdown_threshold = 0.10  # 10%
        
        # Last update
        self.last_update = datetime.now()
    
    def record_trade(self, won: bool, rr: float = 0.0, timestamp: datetime = None) -> None:
        """Record trade result."""
        self.recent_results.append({
            "won": won,
            "rr": rr,
            "timestamp": timestamp or datetime.now()
        })
        self.recent_rr.append(rr)
    
    def record_signal(self, signal, timestamp: datetime = None) -> None:
        """Record signal for frequency tracking."""
        self.recent_signals.append({
            "signal": signal,
            "timestamp": timestamp or datetime.now()
        })
    
    def calculate_health(self) -> SystemHealth:
        """Calculate current system health."""
        health = SystemHealth()
        
        # Win rate (last N)
        if self.recent_results:
            recent_list = list(self.recent_results)
            last_n = recent_list[-self.winrate_window:]
            
            wins = sum(1 for r in last_n if r.get("won", False))
            total = len(last_n)
            
            health.winrate_last_n = wins / total if total > 0 else 0
        
        # Profit factor
        if self.recent_rr:
            profits = sum(r for r in self.recent_rr if r > 0)
            losses = abs(sum(r for r in self.recent_rr if r < 0))
            
            health.profit_factor = profits / losses if losses > 0 else 1.0
        
        # Average R
        if self.recent_rr:
            health.avg_r = sum(self.recent_rr) / len(self.recent_rr)
        
        # Drawdown
        health.drawdown = self._calculate_drawdown()
        
        # Signal frequency (per hour)
        health.signal_frequency = self._calculate_frequency()
        
        health.signal_count = len(self.recent_results)
        
        return health
    
    def _calculate_drawdown(self) -> float:
        """Calculate current drawdown."""
        if not self.recent_rr:
            return 0.0
        
        equity = [10000]
        for rr in self.recent_rr:
            equity.append(equity[-1] * (1 + rr * 0.02))
        
        peak = max(equity)
        current = equity[-1]
        
        return (peak - current) / peak if peak > 0 else 0.0
    
    def _calculate_frequency(self) -> float:
        """Calculate signal frequency per hour."""
        if len(self.recent_signals) < 2:
            return 0.0
        
        # Get time range
        first = self.recent_signals[0]["timestamp"]
        last = self.recent_signals[-1]["timestamp"]
        
        hours = (last - first).total_seconds() / 3600
        
        if hours < 0.1:
            return 0.0
        
        return len(self.recent_signals) / hours
    
    def is_degrading(self) -> bool:
        """Check if system is degrading."""
        health = self.calculate_health()
        
        # Check winrate drop
        if health.winrate_last_n < self.baseline_winrate - self.winrate_drop_threshold:
            return True
        
        # Check PF drop
        if health.profit_factor < self.baseline_pf * (1 - self.pf_drop_threshold):
            return True
        
        # Check drawdown
        if health.drawdown > self.drawdown_threshold:
            return True
        
        return False
    
    def get_degradation_reason(self) -> str:
        """Get reason for degradation."""
        health = self.calculate_health()
        reasons = []
        
        if health.winrate_last_n < self.baseline_winrate - self.winrate_drop_threshold:
            reasons.append(f"winrate ({health.winrate_last_n:.0%} < {self.baseline_winrate:.0%})")
        
        if health.profit_factor < self.baseline_pf * (1 - self.pf_drop_threshold):
            reasons.append(f"PF ({health.profit_factor:.2f} < {self.baseline_pf:.2f})")
        
        if health.drawdown > self.drawdown_threshold:
            reasons.append(f"DD ({health.drawdown:.0%} > {self.drawdown_threshold:.0%})")
        
        return "; ".join(reasons) if reasons else "none"
    
    def set_baseline(self, winrate: float = None, pf: float = None, avg_r: float = None) -> None:
        """Update baseline metrics."""
        if winrate:
            self.baseline_winrate = winrate
        if pf:
            self.baseline_pf = pf
        if avg_r:
            self.baseline_avg_r = avg_r


# System Health Monitor End