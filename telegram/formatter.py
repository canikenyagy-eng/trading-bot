"""
Telegram Formatter - Signal Formatting for Telegram.

This module formats signals for Telegram output with both
short (brief) and full (comprehensive) formats.
"""

from typing import Dict, Optional
from core.signal_engine import (
    SignalEvaluation, SetupGrade, TimingState, Direction
)


class SignalFormatter:
    """Formatter for Telegram signal output."""
    
    def __init__(self, short_enabled: bool = True, full_enabled: bool = True):
        self.short_enabled = short_enabled
        self.full_enabled = full_enabled
    
    def format_short(
        self,
        signal: SignalEvaluation
    ) -> str:
        """Format short signal message.
        
        Args:
            signal: SignalEvaluation
            
        Returns:
            Formatted short message
        """
        if not self.short_enabled:
            return ""
        
        direction_emoji = "🟢" if signal.direction == Direction.LONG else "🔴"
        
        grade_emoji = self._grade_to_emoji(signal.setup_grade)
        
        lines = [
            f"{direction_emoji} {signal.symbol} {signal.direction.value.upper()}",
            f"Entry: {signal.entry:.5f}",
            f"SL: {signal.sl:.5f}",
            f"TP: {signal.tp_levels[0]:.5f}" if signal.tp_levels else "TP: N/A",
            f"R:R: {signal.rr:.1f}",
            f"Conf: {signal.confidence:.0%}",
            f"Grade: {signal.setup_grade.value} {grade_emoji}",
        ]
        
        return "\n".join(lines)
    
    def format_full(
        self,
        signal: SignalEvaluation
    ) -> str:
        """Format full signal message.
        
        Args:
            signal: SignalEvaluation
            
        Returns:
            Formatted full message
        """
        if not self.full_enabled:
            return ""
        
        lines = []
        
        # Header
        direction_emoji = "🟢" if signal.direction == Direction.LONG else "🔴"
        lines.append(f"{direction_emoji} *{signal.symbol} {signal.direction.value.upper()}*")
        lines.append(f"_{signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}_")
        lines.append("")
        
        # Levels
        lines.append("*📊 LEVELS*")
        lines.append(f"Entry: `{signal.entry:.5f}`")
        lines.append(f"SL: `{signal.sl:.5f}`")
        if signal.tp_levels:
            tp_str = ", ".join([f"{tp:.5f}" for tp in signal.tp_levels])
            lines.append(f"TP: `{tp_str}`")
        lines.append(f"RR: *{signal.rr:.2f}*")
        lines.append("")
        
        # Confidence & Grade
        lines.append("*🎯 QUALITY*")
        lines.append(f"Confidence: {signal.confidence:.0%}")
        lines.append(f"Grade: {signal.setup_grade.value}")
        lines.append(f"Timing: {signal.timing.value}")
        lines.append("")
        
        # Probabilities
        if signal.probabilities:
            lines.append("*📈 PROBABILITIES*")
            lines.append(f"TP: {signal.probabilities.tp_hit:.0%}")
            lines.append(f"SL: {signal.probabilities.sl_hit:.0%}")
            lines.append(f"EV: {signal.expected_value:.3f}")
            lines.append("")
        
        # Regime & Phase
        lines.append("*🌊 REGIME*")
        lines.append(f"Regime: {signal.regime.value}")
        lines.append(f"Phase: {signal.market_phase.value}")
        lines.append(f"Session: {signal.session_context.value}")
        lines.append("")
        
        # Features
        if signal.features:
            lines.append("*🔍 FEATURES*")
            for name, feature in signal.features.items():
                status = "✅" if feature.present else "❌"
                strength = f"{feature.strength:.0%}" if feature.present else "-"
                lines.append(f"{status} {name}: {strength}")
            lines.append("")
        
        # Narrative
        if signal.narrative:
            lines.append("*📝 NARRATIVE*")
            if signal.narrative.htf_bias:
                lines.append(f"• HTF: {signal.narrative.htf_bias}")
            if signal.narrative.structure_state:
                lines.append(f"• Structure: {signal.narrative.structure_state}")
            if signal.narrative.entry_logic:
                lines.append(f"• Entry: {signal.narrative.entry_logic}")
            lines.append("")
        
        # Score breakdown
        if signal.score_components:
            lines.append("*📊 SCORE*")
            for comp in signal.score_components:
                lines.append(f"• {comp.feature}: {comp.weighted_score:.2f}")
            lines.append(f"*Total: {signal.total_score:.2f}*")
            lines.append("")
        
        # Rejection reasons
        if signal.rejection_reasons:
            lines.append("*❌ REJECTED*")
            for reason in signal.rejection_reasons:
                lines.append(f"• {reason}")
            lines.append("")
        
        return "\n".join(lines)
    
    def format_accepted(
        self,
        signal: SignalEvaluation
    ) -> str:
        """Format accepted signal for broadcast."""
        lines = []
        
        if self.short_enabled:
            lines.append(self.format_short(signal))
        
        if self.full_enabled and len(lines) > 0:
            lines.append("")
            lines.append("─" * 10)
            lines.append("")
        
        if self.full_enabled:
            lines.append(self.format_full(signal))
        
        return "\n".join(lines)
    
    def format_rejection(
        self,
        signal: SignalEvaluation
    ) -> str:
        """Format rejection notice."""
        lines = [
            f"❌ {signal.symbol} REJECTED",
            f"Time: {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
        ]
        
        if signal.rejection_reasons:
            lines.append("")
            lines.append("Reasons:")
            for reason in signal.rejection_reasons:
                lines.append(f"• {reason}")
        
        return "\n".join(lines)
    
    def _grade_to_emoji(self, grade: SetupGrade) -> str:
        """Convert grade to emoji."""
        mapping = {
            SetupGrade.A_PLUS: "⭐️⭐️⭐️",
            SetupGrade.A: "⭐️⭐️",
            SetupGrade.B: "⭐️",
            SetupGrade.C: "",
        }
        return mapping.get(grade, "")


# Formatter End