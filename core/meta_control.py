"""
Meta-Control - System Health & Self-Adaptation.

Monitors system health and adapts behavior dynamically.

CRITICAL: Analysis only - no auto-trading.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import deque

from config import feature_flags as ff


@dataclass
class SystemHealth:
    """Current system health metrics."""
    
    winrate_last_n: float = 0.5
    drawdown: float = 0.0
    signal_frequency: float = 0.0
    avg_confidence: float = 0.5
    
    # Health status
    is_healthy: bool = True
    status_message: str = ""
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "winrate_last_n": self.winrate_last_n,
            "drawdown": self.drawdown,
            "signal_frequency": self.signal_frequency,
            "avg_confidence": self.avg_confidence,
            "is_healthy": self.is_healthy,
            "status_message": self.status_message,
            "recommendations": self.recommendations,
        }


class MetaControl:
    """Meta-layer system control."""
    
    def __init__(self):
        self.enabled = ff.ENABLE_META_ADAPTATION
        
        # Health parameters
        self.min_winrate = 0.40  # Below this is unhealthy
        self.max_drawdown = 0.15  # 15% drawdown threshold
        self.min_signal_rate = 0.5  # Min signals per day
        
        # Action thresholds
        self.cooldown_threshold = 0.35
        self.strict_threshold = 0.30
        self.relax_threshold = 0.55
        
        # Recent outcomes buffer
        self.recent_outcomes = deque(maxlen=50)
        self.recent_confidences = deque(maxlen=50)
        self.recent_equity = deque(maxlen=100)
        
        # Current adjustments
        self.current_adjustments = {
            "confidence_boost": 0.0,
            "threshold_modifier": 0.0,
            "signal_frequency_modifier": 1.0
        }
    
    def record_trade(
        self,
        result: str,  # "tp", "sl", "be"
        confidence: float
    ) -> None:
        """Record trade for health monitoring."""
        if not self.enabled:
            return
        
        # Record outcome
        won = result == "tp"
        self.recent_outcomes.append(won)
        self.recent_confidences.append(confidence)
        
        # Update equity
        if len(self.recent_equity) == 0:
            self.recent_equity.append(10000)  # Start with 10k
        else:
            last = self.recent_equity[-1]
            rr = 1.0 if won else -1.0
            self.recent_equity.append(last * (1 + rr * 0.02))  # 2% risk
    
    def check_system_health(
        self,
        lookback: int = 20
    ) -> SystemHealth:
        """Check current system health.
        
        Args:
            lookback: Number of trades to analyze
            
        Returns:
            SystemHealth with metrics and recommendations
        """
        health = SystemHealth()
        
        if not self.enabled or len(self.recent_outcomes) < 5:
            health.is_healthy = True
            health.status_message = "insufficient_data"
            return health
        
        # Get recent data
        recent = list(self.recent_outcomes)[-lookback:]
        
        # Calculate winrate
        if recent:
            health.winrate_last_n = sum(recent) / len(recent)
        
        # Calculate drawdown
        health.drawdown = self._calculate_drawdown()
        
        # Signal frequency (normalized)
        health.signal_frequency = len(recent) / lookback if lookback > 0 else 0
        
        # Avg confidence
        if self.recent_confidences:
            recent_conf = list(self.recent_confidences)[-lookback:]
            health.avg_confidence = sum(recent_conf) / len(recent_conf)
        
        # Determine health status
        health.is_healthy = self._evaluate_health(health)
        
        if health.is_healthy:
            health.status_message = "healthy"
        elif health.drawdown > self.max_drawdown:
            health.status_message = "high_drawdown"
        elif health.winrate_last_n < self.cooldown_threshold:
            health.status_message = "poor_performance"
        else:
            health.status_message = "degraded"
        
        # Generate recommendations
        health.recommendations = self._generate_recommendations(health)
        
        # Update adjustments
        self._apply_adaptations(health)
        
        return health
    
    def _calculate_drawdown(self) -> float:
        """Calculate current drawdown."""
        if len(self.recent_equity) < 2:
            return 0.0
        
        equity = list(self.recent_equity)
        peak = max(equity)
        current = equity[-1]
        
        if peak == 0:
            return 0.0
        
        return (peak - current) / peak
    
    def _evaluate_health(self, health: SystemHealth) -> bool:
        """Evaluate if system is healthy."""
        if health.drawdown > self.max_drawdown:
            return False
        
        if health.winrate_last_n < self.min_winrate:
            return False
        
        return True
    
    def _generate_recommendations(
        self,
        health: SystemHealth
    ) -> List[str]:
        """Generate health-based recommendations."""
        recs = []
        
        if health.drawdown > self.max_drawdown:
            recs.append("reduce_position_size")
            recs.append("increase_strictness")
        
        if health.winrate_last_n < self.strict_threshold:
            recs.append("activate_cooldown")
            recs.append("increase_thresholds")
        
        elif health.winrate_last_n < self.cooldown_threshold:
            recs.append("slight_cooldown")
        
        elif health.winrate_last_n > self.relax_threshold:
            recs.append("relax_thresholds")
        
        if health.signal_frequency < self.min_signal_rate:
            recs.append("check_signal_generation")
        
        return recs
    
    def _apply_adaptations(self, health: SystemHealth) -> None:
        """Apply health-based adaptations."""
        # Confidence boost
        if health.status_message == "poor_performance":
            self.current_adjustments["confidence_boost"] = -0.1
        elif health.status_message == "high_drawdown":
            self.current_adjustments["confidence_boost"] = -0.15
        else:
            self.current_adjustments["confidence_boost"] = 0
        
        # Threshold modifier
        if health.drawdown > self.max_drawdown * 0.8:
            self.current_adjustments["threshold_modifier"] = 0.05
        else:
            self.current_adjustments["threshold_modifier"] = 0
        
        # Signal frequency
        if health.signal_frequency < 0.3:
            self.current_adjustments["signal_frequency_modifier"] = 0.8
        else:
            self.current_adjustments["signal_frequency_modifier"] = 1.0
    
    def get_adjusted_threshold(
        self,
        base_threshold: float
    ) -> float:
        """Get health-adjusted threshold."""
        if not self.enabled:
            return base_threshold
        
        return base_threshold + self.current_adjustments["threshold_modifier"]
    
    def get_confidence_adjustment(
        self,
        base_confidence: float
    ) -> float:
        """Get health-adjusted confidence."""
        if not self.enabled:
            return base_confidence
        
        return base_confidence + self.current_adjustments["confidence_boost"]
    
    def should_suppress_signal(
        self,
        confidence: float
    ) -> bool:
        """Check if signal should be suppressed."""
        if not self.enabled:
            return False
        
        if self.current_adjustments["signal_frequency_modifier"] < 0.9:
            # Random suppression
            import random
            return random.random() > self.current_adjustments["signal_frequency_modifier"]
        
        return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get full system status."""
        health = self.check_system_health()
        
        return {
            **health.to_dict(),
            "current_adjustments": self.current_adjustments,
            "total_trades": len(self.recent_outcomes)
        }
    
    def reset(self) -> None:
        """Reset health tracking."""
        self.recent_outcomes.clear()
        self.recent_confidences.clear()
        self.recent_equity.clear()
        self.current_adjustments = {
            "confidence_boost": 0.0,
            "threshold_modifier": 0.0,
            "signal_frequency_modifier": 1.0
        }


# Meta-Control End