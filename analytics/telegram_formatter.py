"""
Telegram Signal Formatter - Signal Output Formatting.

This module formats signals for Telegram output with SHORT and FULL formats.

CRITICAL: Analysis-only. No auto-trading.
"""

from typing import Dict, List, Optional, Any


class SignalFormatter:
    """Formatter for Telegram signal output."""
    
    # Emoji map
    EMOJI = {
        "long": "🟢",
        "short": "🔴",
        "buy": "🟢",
        "sell": "🔴",
        "up": "📈",
        "down": "📉",
        "check": "✅",
        "cross": "❌",
        "warning": "⚠️",
        "fire": "🔥",
        "brain": "🧠",
        "target": "🎯",
        "stop": "🛑",
        "info": "ℹ️",
    }
    
    def __init__(self, verbose: bool = True, use_html: bool = True):
        """Initialize formatter.
        
        Args:
            verbose: If True, use FULL format. If False, use SHORT.
            use_html: If True, use HTML. If False, use Markdown.
        """
        self.verbose = verbose
        self.use_html = use_html
    
    def _wrap(self, text: str, bold: bool = False) -> str:
        """Wrap text with formatting."""
        if self.use_html:
            return f"<b>{text}</b>" if bold else text
        else:
            return f"*{text}*" if bold else text
    
    def _wrap_code(self, text: str) -> str:
        """Wrap text as code."""
        if self.use_html:
            return f"<code>{text}</code>"
        else:
            return f"`{text}`"
    
    def format_signal(
        self,
        signal,
        include_narrative: bool = True
    ) -> str:
        """Format signal for Telegram output.
        
        Args:
            signal: SignalEvaluation to format
            include_narrative: Include narrative details
            
        Returns:
            Formatted Telegram message
        """
        if self.verbose:
            return self._format_full(signal, include_narrative)
        else:
            return self._format_short(signal)
    
    def _format_short(self, signal) -> str:
        """Format SHORT signal message."""
        direction_emoji = self.EMOJI.get(signal.direction.value, "📊")
        
        # Entry line with bold wrap for emoji
        entry_line = f"{direction_emoji} {self._wrap(signal.direction.value.upper(), bold=True)} {signal.symbol}"
        
        # Levels
        levels = [
            f"Entry: {signal.entry:.5f}",
            f"SL: {signal.sl:.5f}",
        ]
        if signal.tp_levels:
            tps = ", ".join([f"TP{i+1}: {tp:.5f}" for i, tp in enumerate(signal.tp_levels)])
            levels.append(tps)
        
        # Build message
        lines = [
            entry_line,
            *levels,
            f"",
            f"Confidence: {signal.confidence:.0%}",
            f"RR: {signal.rr:.1f}",
            f"Timing: {signal.timing.value}",
        ]
        
        # Rejection reasons
        if signal.is_rejected:
            lines.append("")
            lines.append("❌ REJECTED")
            for reason in signal.rejection_reasons:
                lines.append(f"  • {reason}")
        
        return "\n".join(lines)
    
    def _format_full(self, signal, include_narrative: bool = True) -> str:
        """Format FULL signal message with all details."""
        direction_emoji = self.EMOJI.get(signal.direction.value, "📊")
        
        # Header
        lines = [
            f"{direction_emoji} {self._wrap(signal.direction.value.upper(), bold=True)} {signal.symbol}",
            f"ID: {self._wrap_code(signal.signal_id)}",
            "",
        ]
        
        # Use helper for section headers
        def section(title):
            return f"📊 {self._wrap(title, bold=True)}"
        
        lines.append(section("LEVELS"))
        lines.append(f"Entry: {signal.entry:.5f}")
        lines.append(f"Stop: {signal.sl:.5f}")
        if signal.tp_levels:
            for i, tp in enumerate(signal.tp_levels):
                lines.append(f"TP{i+1}: {tp:.5f}")
        lines.append(f"RR: {signal.rr:.1f}")
        lines.append("")
        
        # Quality section
        lines.append(section("QUALITY"))
        lines.append(f"Grade: {signal.setup_grade.value}")
        lines.append(f"Confidence: {signal.confidence:.0%}")
        lines.append(f"Timing: {signal.timing.value}")
        
        # Confidence breakdown
        if signal.confidence_components:
            cc = signal.confidence_components
            lines.append("")
            lines.append(section("BREAKDOWN"))
            lines.append(f"Structure: {cc.structure:.0%}")
            lines.append(f"Liquidity: {cc.liquidity:.0%}")
            lines.append(f"Entry: {cc.entry_quality:.0%}")
            lines.append(f"Regime Fit: {cc.regime_fit:.0%}")
        
        # Probabilities
        if signal.probabilities:
            pr = signal.probabilities
            lines.append("")
            lines.append("🎲 Probabilities")
            lines.append(f"TP Hit: {pr.tp_hit:.0%}")
            lines.append(f"SL Hit: {pr.sl_hit:.0%}")
        
        # Expected Value
        if signal.expected_value != 0:
            lines.append("")
            ev_emoji = "🟢" if signal.expected_value > 0 else "🔴"
            lines.append(f"{ev_emoji} EV: {signal.expected_value:.2f}")
        
        # Market Context
        lines.append("")
        lines.append("🌊 Market Context")
        lines.append(f"Regime: {signal.regime.value}")
        lines.append(f"Phase: {signal.market_phase.value}")
        
        # Features
        if signal.features:
            lines.append("")
            lines.append("🔍 Features")
            for name, feature in signal.features.items():
                status = "✅" if feature.present else "❌"
                lines.append(f"{status} {name}: {feature.strength:.0%}")
        
        # Narrative
        if include_narrative and signal.narrative:
            lines.append("")
            lines.append("📝 Narrative")
            if signal.narrative.htf_bias:
                lines.append(f"HTF: {signal.narrative.htf_bias}")
            if signal.narrative.structure_state:
                lines.append(f"Structure: {signal.narrative.structure_state}")
        
        # Rejection
        if signal.is_rejected:
            lines.append("")
            lines.append("❌ REJECTED")
            for reason in signal.rejection_reasons:
                lines.append(f"  • {reason}")
        
        return "\n".join(lines)
    
    def format_signal_list(self, signals, max_count: int = 5) -> str:
        """Format list of signals."""
        if not signals:
            return "No signals available."
        
        lines = [f"📊 Signals ({len(signals)})", ""]
        
        for i, signal in enumerate(signals[:max_count]):
            emoji = self.EMOJI.get(signal.direction.value, "📊")
            lines.append(
                f"{i+1}. {emoji} {signal.symbol} "
                f"{signal.direction.value.upper()} @ {signal.entry:.5f}"
            )
        
        if len(signals) > max_count:
            lines.append(f"... and {len(signals) - max_count} more")
        
        return "\n".join(lines)
    
    def format_performance_summary(self, metrics: Dict[str, Any]) -> str:
        """Format performance metrics summary."""
        lines = ["📊 Performance Summary", ""]
        
        if "win_rate" in metrics:
            lines.append(f"Win Rate: {metrics['win_rate']:.1%}")
        if "total_trades" in metrics:
            lines.append(f"Trades: {metrics['total_trades']}")
        if "avg_r" in metrics:
            lines.append(f"Avg R: {metrics['avg_r']:.2f}")
        if "profit_factor" in metrics:
            lines.append(f"Profit Factor: {metrics['profit_factor']:.2f}")
        if "max_drawdown" in metrics:
            lines.append(f"Max DD: {metrics['max_drawdown']:.1%}")
        
        return "\n".join(lines)


# Telegram Formatter End