"""
Adaptive Aggression Controller - Mode-Based Behavior Control.

Controls system aggressiveness based on health and market conditions.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from core.system_health import SystemHealthMonitor, SystemHealth


class SystemMode(Enum):
    """System operating modes."""
    NORMAL = "normal"
    DEFENSIVE = "defensive"
    CONSERVATIVE = "conservative"
    HALT = "halt"
    RECOVERING = "recovering"


class AdaptiveAggressionController:
    """Adaptive aggression control system."""
    
    def __init__(self):
        self.monitor = SystemHealthMonitor()
        
        # Mode thresholds
        self.defensive_drawdown = 0.05  # 5%
        self.conservative_drawdown = 0.10  # 10%
        self.halt_drawdown = 0.15  # 15%
        
        self.defensive_wr_drop = 0.08  # 8%
        self.conservative_wr_drop = 0.12  # 12%
        
        self.defensive_pf_drop = 0.25  # 25%
        self.conservative_pf_drop = 0.40  # 40%
        
        # Mode parameters
        self.mode_params = {
            SystemMode.NORMAL: {
                "top_n": 3,
                "min_confidence": 0.3,
                "min_ev": -0.1,
                "risk_percent": 0.02,
                "allowed_signals": 3,
            },
            SystemMode.DEFENSIVE: {
                "top_n": 2,
                "min_confidence": 0.4,
                "min_ev": 0.0,
                "risk_percent": 0.015,
                "allowed_signals": 2,
            },
            SystemMode.CONSERVATIVE: {
                "top_n": 1,
                "min_confidence": 0.5,
                "min_ev": 0.1,
                "risk_percent": 0.01,
                "allowed_signals": 1,
            },
            SystemMode.HALT: {
                "top_n": 0,
                "min_confidence": 1.0,
                "min_ev": 1.0,
                "risk_percent": 0.0,
                "allowed_signals": 0,
            },
            SystemMode.RECOVERING: {
                "top_n": 2,
                "min_confidence": 0.35,
                "min_ev": -0.05,
                "risk_percent": 0.015,
                "allowed_signals": 2,
            },
        }
        
        # Current mode
        self.current_mode = SystemMode.NORMAL
        
        # Mode history for recovery tracking
        self.mode_history: Dict[str, int] = {}
        self.consecutive_normal = 0
        self.recovery_counter = 0
        
        # Recovery thresholds
        self.recovery_wr = 0.52  # 52%
        self.recovery_drawdown = 0.03  # 3%
        self.recovery_required = 10  # trades
    
    def update_mode(self) -> SystemMode:
        """Update system mode based on health."""
        health = self.monitor.calculate_health()
        
        old_mode = self.current_mode
        
        # Check halt first (most restrictive)
        if health.drawdown > self.halt_drawdown:
            self.current_mode = SystemMode.HALT
        
        # Check conservative
        elif health.drawdown > self.conservative_drawdown or \
             health.winrate_last_n < self.baseline_wr - self.conservative_wr_drop:
            self.current_mode = SystemMode.CONSERVATIVE
        
        # Check defensive
        elif health.drawdown > self.defensive_drawdown or \
             health.winrate_last_n < self.baseline_wr - self.defensive_wr_drop:
            self.current_mode = SystemMode.DEFENSIVE
        
        # Check recovery (if previously in non-normal)
        elif self.current_mode != SystemMode.NORMAL:
            if self._check_recovery(health):
                self.current_mode = SystemMode.RECOVERING
            else:
                self.current_mode = SystemMode.NORMAL
        
        # Track mode changes
        mode_key = self.current_mode.value
        self.mode_history[mode_key] = self.mode_history.get(mode_key, 0) + 1
        
        if self.current_mode == SystemMode.NORMAL:
            self.consecutive_normal += 1
        else:
            self.consecutive_normal = 0
        
        return self.current_mode
    
    @property
    def baseline_wr(self) -> float:
        return self.monitor.baseline_winrate
    
    def _check_recovery(self, health: SystemHealth) -> bool:
        """Check if system has recovered enough."""
        # Check metrics
        if health.drawdown > self.recovery_drawdown:
            return False
        
        if health.winrate_last_n < self.recovery_wr:
            return False
        
        # Check trade count
        if health.signal_count < self.recovery_required:
            return False
        
        return True
    
    def get_mode_params(self) -> Dict[str, Any]:
        """Get parameters for current mode."""
        return self.mode_params.get(self.current_mode, self.mode_params[SystemMode.NORMAL])
    
    def get_allowed_signals(self) -> int:
        """Get number of allowed signals."""
        return self.get_mode_params()["allowed_signals"]
    
    def get_min_confidence(self) -> float:
        """Get minimum confidence threshold."""
        return self.get_mode_params()["min_confidence"]
    
    def get_min_ev(self) -> float:
        """Get minimum EV threshold."""
        return self.get_mode_params()["min_ev"]
    
    def get_risk_percent(self) -> float:
        """Get risk percent."""
        return self.get_mode_params()["risk_percent"]
    
    def is_paused(self) -> bool:
        """Check if system is paused."""
        return self.current_mode == SystemMode.HALT
    
    def should_suppress(self) -> bool:
        """Check if signals should be suppressed."""
        return self.current_mode in (SystemMode.CONSERVATIVE, SystemMode.HALT)
    
    def get_status_report(self) -> Dict[str, Any]:
        """Get full status report."""
        health = self.monitor.calculate_health()
        params = self.get_mode_params()
        
        return {
            "mode": self.current_mode.value,
            "health": health.to_dict(),
            "params": params,
            "is_paused": self.is_paused(),
            "should_suppress": self.should_suppress(),
            "mode_history": self.mode_history,
            "degradation_reason": self.monitor.get_degradation_reason(),
        }


# Adaptive Aggression Controller End