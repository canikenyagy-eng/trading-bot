"""
Entry Logic Engine - Multiple Entry Models.

This module implements multiple entry models:
- Mitigation entry (enter at mitigation zone)
- Classic entry (enter at structure confirmation)
- Adaptive selection between models based on performance

CRITICAL: This is analysis only. No trade execution.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from core.signal_engine import SignalEvaluation, Direction
from config import feature_flags as ff


class EntryType(str, Enum):
    """Entry type."""
    MITIGATION = "mitigation"     # Enter at mitigation zone
    CLASSIC = "classic"          # Enter at structure confirmation
    MARKET = "market"           # Enter at market (if no zones)
    PENDING = "pending"        # Wait for better price


@dataclass
class EntryResult:
    """Result of entry logic."""
    
    # Chosen entry
    entry_type: EntryType = EntryType.CLASSIC
    
    # Entry prices
    entry_price: float = 0.0
    limit_price: Optional[float] = None  # For limit orders
    
    # Timing
    timing: str = "immediate"  # "immediate", "wait", "skip"
    wait_bars: int = 0
    
    # Reasoning
    selection_reason: str = ""
    
    # Confidence adjustment (due to entry choice)
    confidence_adjustment: float = 1.0
    
    # Alternative options
    alternatives: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_type": self.entry_type.value,
            "entry_price": self.entry_price,
            "limit_price": self.limit_price,
            "timing": self.timing,
            "wait_bars": self.wait_bars,
            "selection_reason": self.selection_reason,
            "confidence_adjustment": self.confidence_adjustment,
            "alternatives": self.alternatives,
        }


class EntryEngine:
    """Engine for entry logic selection.
    
    This selects between entry types based on setup quality
    and historical performance.
    
    CRITICAL: Analysis only. No trade execution.
    """
    
    def __init__(self):
        # Entry model parameters
        self.mitigation_weight = 1.0
        self.classic_weight = 1.0
        
        # Cooldown
        self.cooldown_minutes = 15
        self._last_entry_time: Optional[datetime] = None
        self._entry_history: List[Dict] = []
        
        # Adaptive parameters
        self.use_adaptive_selection = ff.ENABLE_ADAPTIVE_RR
        
        # Performance tracking per entry type
        self._mitigation_performance: List[bool] = []
        self._classic_performance: List[bool] = []
        
        # Entry thresholds
        self.min_mitigation_strength = 0.5
        self.min_classic_strength = 0.4
        self.confidence_threshold = 0.30
    
    def calculate_entry(
        self,
        signal: SignalEvaluation
    ) -> EntryResult:
        """Calculate entry for signal.
        
        Args:
            signal: SignalEvaluation
            
        Returns:
            EntryResult with entry details
        """
        result = EntryResult()
        
        # Check features for entry options
        mitigation_feature = signal.features.get("mitigation")
        fvg_feature = signal.features.get("fvg")
        ob_feature = signal.features.get("order_block")
        structure_feature = signal.features.get("structure")
        
        # Evaluate entry options
        mitigation_score = self._evaluate_mitigation(mitigation_feature, fvg_feature, signal)
        classic_score = self._evaluate_classic(structure_feature, ob_feature, signal)
        
        # Get confidence factor
        confidence = signal.confidence
        
        # Decision logic
        result = self._make_decision(
            signal, mitigation_score, classic_score, confidence
        )
        
        # Record for adaptive learning
        self._record_entry_attempt(signal, result)
        
        return result
    
    def _evaluate_mitigation(
        self,
        mitigation_feature: Any,
        fvg_feature: Any,
        signal: SignalEvaluation
    ) -> float:
        """Evaluate mitigation entry score."""
        score = 0.0
        
        # Need mitigation feature
        if mitigation_feature and mitigation_feature.present:
            score += 0.5
            
            if mitigation_feature.strength >= self.min_mitigation_strength:
                score += 0.3
            
            # Recent (not old)
            if mitigation_feature.age <= 3:
                score += 0.2
        
        # FVG confirms direction
        if fvg_feature and fvg_feature.present:
            score += 0.2
        
        return min(score, 1.0)
    
    def _evaluate_classic(
        self,
        structure_feature: Any,
        ob_feature: Any,
        signal: SignalEvaluation
    ) -> float:
        """Evaluate classic entry score."""
        score = 0.0
        
        # Need structure
        if structure_feature and structure_feature.present:
            score += 0.4
            
            if structure_feature.strength >= self.min_classic_strength:
                score += 0.2
        
        # Order block confirms
        if ob_feature and ob_feature.present:
            score += 0.3
        
        return min(score, 1.0)
    
    def _make_decision(
        self,
        signal: SignalEvaluation,
        mitigation_score: float,
        classic_score: float,
        confidence: float
    ) -> EntryResult:
        """Make entry decision."""
        result = EntryResult()
        
        # Apply adaptive weights
        if self.use_adaptive_selection:
            mitigation_score *= self.mitigation_weight
            classic_score *= self.classic_weight
        
        # Low confidence = skip
        if confidence < self.confidence_threshold:
            result.entry_type = EntryType.PENDING
            result.timing = "skip"
            result.selection_reason = "confidence_below_threshold"
            result.confidence_adjustment = 0.0
            return result
        
        # Score comparison
        if mitigation_score > classic_score:
            result.entry_type = EntryType.MITIGATION
            result.selection_reason = f"mitigation_stronger_{mitigation_score:.2f}_vs_{classic_score:.2f}"
            
            if signal.features.get("mitigation"):
                entry_level = signal.features["mitigation"].details.get("mid", signal.entry)
                result.entry_price = entry_level
                result.limit_price = signal.entry  # Enter at limit if available
            
            result.confidence_adjustment = min(mitigation_score * 1.1, 1.0)
            result.timing = "immediate"
            
        elif classic_score > 0:
            result.entry_type = EntryType.CLASSIC
            result.selection_reason = f"classic_stronger_{classic_score:.2f}_vs_{mitigation_score:.2f}"
            result.entry_price = signal.entry
            result.confidence_adjustment = min(classic_score * 1.1, 1.0)
            result.timing = "immediate"
        
        else:
            # No clear entry, use market
            result.entry_type = EntryType.MARKET
            result.entry_price = signal.entry
            result.selection_reason = "fallback_to_market"
            result.confidence_adjustment = 0.8
            result.timing = "immediate"
        
        # Alternatives
        if mitigation_score > 0:
            result.alternatives.append({
                "type": "mitigation",
                "score": mitigation_score,
            })
        if classic_score > 0:
            result.alternatives.append({
                "type": "classic", 
                "score": classic_score,
            })
        
        return result
    
    def _record_entry_attempt(
        self,
        signal: SignalEvaluation,
        result: EntryResult
    ) -> None:
        """Record entry attempt for adaptive learning."""
        # Check cooldown
        now = datetime.now()
        
        if self._last_entry_time:
            minutes_since = (now - self._last_entry_time).total_seconds() / 60
            if minutes_since < self.cooldown_minutes:
                result.wait_bars = self.cooldown_minutes - int(minutes_since)
                result.timing = "wait"
        
        self._last_entry_time = now
        
        self._entry_history.append({
            "signal_id": signal.signal_id,
            "entry_type": result.entry_type.value,
            "entry_price": result.entry_price,
            "timestamp": now.isoformat(),
        })
    
    def record_outcome(
        self,
        signal_id: str,
        entry_type: str,
        tp_hit: bool
    ) -> None:
        """Record outcome for entry type performance."""
        if entry_type == "mitigation":
            self._mitigation_performance.append(tp_hit)
        elif entry_type == "classic":
            self._classic_performance.append(tp_hit)
        
        # Keep only recent
        if len(self._mitigation_performance) > 50:
            self._mitigation_performance.pop(0)
        if len(self._classic_performance) > 50:
            self._classic_performance.pop(0)
        
        # Update weights adaptive
        if self.use_adaptive_selection:
            self._update_weights()
    
    def _update_weights(self) -> None:
        """Update entry weights based on performance."""
        if len(self._mitigation_performance) < 10 or len(self._classic_performance) < 10:
            return
        
        import statistics
        
        mit_wr = sum(self._mitigation_performance) / len(self._mitigation_performance)
        classic_wr = sum(self._classic_performance) / len(self._classic_performance)
        
        # Increase weight for better performer
        if mit_wr > classic_wr + 0.05:
            self.mitigation_weight = min(self.mitigation_weight * 1.1, 2.0)
            self.classic_weight = max(self.classic_weight * 0.9, 0.5)
        elif classic_wr > mit_wr + 0.05:
            self.classic_weight = min(self.classic_weight * 1.1, 2.0)
            self.mitigation_weight = max(self.mitigation_weight * 0.9, 0.5)
    
    def get_cooldown_status(
        self
    ) -> Dict[str, Any]:
        """Get cooldown status."""
        if not self._last_entry_time:
            return {"on_cooldown": False, "remaining_minutes": 0}
        
        minutes_since = (datetime.now() - self._last_entry_time).total_seconds() / 60
        remaining = max(0, self.cooldown_minutes - minutes_since)
        
        return {
            "on_cooldown": remaining > 0,
            "remaining_minutes": int(remaining),
        }
    
    def get_performance_by_entry_type(
        self
    ) -> Dict[str, float]:
        """Get performance by entry type."""
        import statistics
        
        result = {}
        
        if self._mitigation_performance:
            result["mitigation_winrate"] = sum(self._mitigation_performance) / len(self._mitigation_performance)
            result["mitigation_trades"] = len(self._mitigation_performance)
        
        if self._classic_performance:
            result["classic_winrate"] = sum(self._classic_performance) / len(self._classic_performance)
            result["classic_trades"] = len(self._classic_performance)
        
        result["mitigation_weight"] = self.mitigation_weight
        result["classic_weight"] = self.classic_weight
        
        return result
    
    def force_entry_type(
        self,
        entry_type: EntryType
    ) -> None:
        """Force specific entry type (for testing)."""
        if entry_type == EntryType.MITIGATION:
            self.mitigation_weight = 2.0
            self.classic_weight = 0.5
        elif entry_type == EntryType.CLASSIC:
            self.classic_weight = 2.0
            self.mitigation_weight = 0.5
        else:
            self.mitigation_weight = 1.0
            self.classic_weight = 1.0


# Entry Logic End