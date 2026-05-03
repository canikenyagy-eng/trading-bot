"""
System Alerting - Live System Status Alerts.

Sends real-time system status to Telegram.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

from core.system_health import SystemHealthMonitor
from core.adaptive_control import AdaptiveAggressionController, SystemMode


class SystemAlert:
    """System alert for Telegram."""
    
    def __init__(self):
        self.enabled = True
        
        # Alert thresholds
        self.alerts_on_mode_change = True
        self.alerts_on_threshold = True
        self.alerts_on_pause = True
        
        # Last alert tracking
        self.last_mode = SystemMode.NORMAL
    
    def format_health_alert(
        self,
        monitor: SystemHealthMonitor,
        controller: AdaptiveAggressionController
    ) -> str:
        """Format health status alert."""
        health = monitor.calculate_health()
        mode = controller.current_mode
        
        # Build message
        lines = [
            "📊 SYSTEM STATUS",
            f"Mode: {mode.value.upper()}",
            "",
            "Health:",
            f"  Win Rate (last {monitor.winrate_window}): {health.winrate_last_n:.1%}",
            f"  Profit Factor: {health.profit_factor:.2f}",
            f"  Drawdown: {health.drawdown:.1%}",
            f"  Avg R: {health.avg_r:.2f}",
            f"  Signals: {health.signal_count}",
        ]
        
        # Add degradation warning
        if monitor.is_degrading():
            lines.append("")
            lines.append(f"⚠️ DEGRADING: {monitor.get_degradation_reason()}")
        
        return "\n".join(lines)
    
    def format_mode_change_alert(
        self,
        old_mode: SystemMode,
        new_mode: SystemMode,
        reason: str = ""
    ) -> str:
        """Format mode change alert."""
        lines = [
            f"🔄 MODE CHANGE",
            f"From: {old_mode.value}",
            f"To: {new_mode.value}",
        ]
        
        if reason:
            lines.append(f"Reason: {reason}")
        
        return "\n".join(lines)
    
    def format_pause_alert(
        self,
        drawdown: float,
        reason: str = ""
    ) -> str:
        """Format pause alert."""
        lines = [
            "🛑 SYSTEM PAUSED",
            f"Drawdown: {drawdown:.1%}",
        ]
        
        if reason:
            lines.append(f"Reason: {reason}")
        
        return "\n".join(lines)
    
    def format_recovery_alert(
        self,
        health,
        mode: SystemMode
    ) -> str:
        """Format recovery alert."""
        lines = [
            "✅ RECOVERY DETECTED",
            f"New Mode: {mode.value}",
            f"Win Rate: {health.winrate_last_n:.1%}",
            f"Drawdown: {health.drawdown:.1%}",
        ]
        
        return "\n".join(lines)
    
    def should_alert(
        self,
        controller: AdaptiveAggressionController
    ) -> bool:
        """Check if alert should be sent."""
        mode = controller.current_mode
        
        # Mode change
        if self.alerts_on_mode_change and mode != self.last_mode:
            self.last_mode = mode
            return True
        
        # Threshold breach
        if self.alerts_on_threshold and controller.monitor.is_degrading():
            return True
        
        # Pause
        if self.alerts_on_pause and controller.is_paused():
            return True
        
        return False
    
    def send_if_needed(
        self,
        monitor: SystemHealthMonitor,
        controller: AdaptiveAggressionController,
        bot = None
    ) -> Optional[str]:
        """Send alert if needed."""
        if not self.should_alert(controller):
            return None
        
        message = self.format_health_alert(monitor, controller)
        
        # TODO: Send via bot if provided
        # if bot:
        #     bot.send_message(message)
        
        return message


# System Alerting End