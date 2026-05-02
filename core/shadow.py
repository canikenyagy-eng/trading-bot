"""
Shadow Scoring Engine - Parallel Scoring without Signal Disruption.

This module implements SHADOW scoring that runs parallel to the main
signal flow. It calculates alternative scores without affecting the actual
signals emitted.

CRITICAL: This is analysis-only. Does NOT affect actual trading signals.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from core.signal_engine import SignalEvaluation, FeatureBreakdown, Direction
from core import scoring as main_scoring
from core import confidence as main_confidence
from config import feature_flags as ff


@dataclass
class ShadowScore:
    """Shadow score result for a single signal."""
    
    signal_id: str
    
    # Shadow calculations
    total_score: float = 0.0
    confidence: float = 0.0
    expected_value: float = 0.0
    
    # Component breakdown
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    
    # Comparison with main signal
    score_delta: float = 0.0
    confidence_delta: float = 0.0
    
    # Timestamp
    calculated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "total_score": self.total_score,
            "confidence": self.confidence,
            "expected_value": self.expected_value,
            "score_breakdown": self.score_breakdown,
            "score_delta": self.score_delta,
            "confidence_delta": self.confidence_delta,
            "calculated_at": self.calculated_at.isoformat(),
        }


@dataclass
class ShadowMetrics:
    """Aggregated shadow scoring metrics."""
    
    # Counters
    signals_evaluated: int = 0
    signals_above_threshold: int = 0
    signals_below_threshold: int = 0
    
    # Averaged metrics
    avg_score: float = 0.0
    avg_confidence: float = 0.0
    avg_ev: float = 0.0
    
    # Variance
    score_variance: float = 0.0
    confidence_variance: float = 0.0
    
    # Performance estimates (based on shadow scores)
    estimated_winrate: float = 0.5
    estimated_profit_factor: float = 0.0
    
    # By feature
    feature_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "signals_evaluated": self.signals_evaluated,
            "signals_above_threshold": self.signals_above_threshold,
            "signals_below_threshold": self.signals_below_threshold,
            "avg_score": self.avg_score,
            "avg_confidence": self.avg_confidence,
            "avg_ev": self.avg_ev,
            "score_variance": self.score_variance,
            "confidence_variance": self.confidence_variance,
            "estimated_winrate": self.estimated_winrate,
            "estimated_profit_factor": self.estimated_profit_factor,
            "feature_performance": self.feature_performance,
        }


class ShadowScoringEngine:
    """Engine for shadow scoring.
    
    CRITICAL: This runs PARALLEL to main signal flow.
    Does NOT affect actual signal emission.
    """
    
    def __init__(self):
        self.enabled = ff.ENABLE_SHADOW_MODE
        
        # Shadow engines
        self.shadow_scoring = main_scoring.ScoringEngine()
        self.shadow_confidence = main_confidence.ConfidenceEngine(self.shadow_scoring)
        
        # Shadow weight adjustments (different from main)
        self.shadow_weights = main_scoring.ScoringWeights()
        self._adjust_shadow_weights()
        
        # History
        self.shadow_history: List[ShadowScore] = []
        
        # Metrics
        self.metrics = ShadowMetrics()
        
        # Thresholds
        self.shadow_threshold = 0.4  # Confidence threshold for shadow acceptance
    
    def _adjust_shadow_weights(self) -> None:
        """Adjust weights for shadow scoring.
        
        Shadow uses slightly different weights to test variations.
        """
        # Increase some weights to test sensitivity
        self.shadow_weights.structure *= 1.2
        self.shadow_weights.fvg *= 1.1
        self.shadow_weights.mitigation *= 1.15
    
    def evaluate_signal(
        self,
        signal: SignalEvaluation
    ) -> ShadowScore:
        """Evaluate a signal with shadow scoring.
        
        CRITICAL: This runs COMPLETELY INDEPENDENT of main signal flow.
        Uses separate shadow engines WITHOUT modifying the original signal.
        
        Args:
            signal: SignalEvaluation from main flow
            
        Returns:
            ShadowScore with shadow calculations only
        """
        if not self.enabled:
            return ShadowScore(signal_id=signal.signal_id)
        
        # Create shadow score result - does not modify original signal
        shadow_score = ShadowScore(signal_id=signal.signal_id)
        
        # Store original confidence for comparison
        original_confidence = signal.confidence
        
        # Run independent shadow calculations (non-disruptive mode)
        shadow_score.total_score = self.shadow_scoring.calculate_total_score(signal)
        
        # Use non-disruptive confidence calculation (update_signal=False)
        shadow_conf = self.shadow_confidence.calculate_confidence(signal, update_signal=False)
        
        # Store shadow confidence - does NOT modify signal
        shadow_score.confidence = shadow_conf
        
        # Calculate score breakdown using shadow engine
        shadow_score.score_breakdown = self.shadow_scoring.get_score_breakdown(signal)
        
        # Calculate EV if enabled
        if ff.ENABLE_EV:
            from core.ev import ExpectedValueEngine
            ev_engine = ExpectedValueEngine()
            shadow_score.expected_value = ev_engine.calculate_ev(signal)
        
        # Calculate deltas (shadow vs main signal's original values)
        shadow_score.score_delta = shadow_score.total_score - 0.0  # Main flow may not have computed score yet
        shadow_score.confidence_delta = shadow_score.confidence - original_confidence
        
        # Store in history
        self.shadow_history.append(shadow_score)
        
        # Update metrics
        self._update_metrics(shadow_score)
        
        # CRITICAL: Signal object is NOT modified by shadow scoring
        # Main signal flow continues with original calculated values
        
        return shadow_score
    
    def _apply_shadow_weights(
        self,
        signal: SignalEvaluation
    ) -> None:
        """Apply shadow weights to signal features."""
        # Shadow scoring uses different weight calculations
        # This is done by modifying the scoring engine's weights temporarily
    
    def _update_metrics(
        self,
        shadow_score: ShadowScore
    ) -> None:
        """Update shadow metrics with new score."""
        self.metrics.signals_evaluated += 1
        
        if shadow_score.confidence >= self.shadow_threshold:
            self.metrics.signals_above_threshold += 1
        else:
            self.metrics.signals_below_threshold += 1
        
        # Update averages
        n = self.metrics.signals_evaluated
        self.metrics.avg_score = (
            (self.metrics.avg_score * (n - 1) + shadow_score.total_score) / n
        )
        self.metrics.avg_confidence = (
            (self.metrics.avg_confidence * (n - 1) + shadow_score.confidence) / n
        )
        
        if ff.ENABLE_EV:
            self.metrics.avg_ev = (
                (self.metrics.avg_ev * (n - 1) + shadow_score.expected_value) / n
            )
        
        # Update feature performance
        self._update_feature_performance(shadow_score)
    
    def _update_feature_performance(
        self,
        shadow_score: ShadowScore
    ) -> None:
        """Update performance tracked by feature."""
        for feature, score in shadow_score.score_breakdown.items():
            if feature == "total":
                continue
            
            if feature not in self.metrics.feature_performance:
                self.metrics.feature_performance[feature] = {
                    "avg_score": 0.0,
                    "count": 0,
                    "total_score": 0.0,
                }
            
            fp = self.metrics.feature_performance[feature]
            fp["count"] += 1
            fp["total_score"] += score
            fp["avg_score"] = fp["total_score"] / fp["count"]
    
    def get_recent_performance(
        self,
        n: int = 50
    ) -> Dict[str, float]:
        """Get recent performance from shadow scores.
        
        Args:
            n: Number of recent scores
            
        Returns:
            Dictionary of performance metrics
        """
        if not self.shadow_history:
            return {
                "avg_confidence": 0.0,
                "avg_score": 0.0,
                "above_threshold_rate": 0.0,
            }
        
        recent = self.shadow_history[-n:]
        
        avg_confidence = sum(s.confidence for s in recent) / len(recent)
        avg_score = sum(s.total_score for s in recent) / len(recent)
        above_rate = sum(1 for s in recent if s.confidence >= self.shadow_threshold) / len(recent)
        
        return {
            "avg_confidence": avg_confidence,
            "avg_score": avg_score,
            "above_threshold_rate": above_rate,
        }
    
    def compare_signals(
        self,
        signal: SignalEvaluation,
        shadow_score: ShadowScore
    ) -> Dict[str, Any]:
        """Compare main signal with shadow score.
        
        Args:
            signal: Main signal
            shadow_score: Shadow score
            
        Returns:
            Comparison dictionary
        """
        return {
            "signal_id": signal.signal_id,
            "symbol": signal.symbol,
            "direction": signal.direction.value,
            "main_confidence": signal.confidence,
            "shadow_confidence": shadow_score.confidence,
            "confidence_delta": shadow_score.confidence_delta,
            "main_score": signal.total_score,
            "shadow_score": shadow_score.total_score,
            "score_delta": shadow_score.score_delta,
            "recommendation": self._get_recommendation(shadow_score),
        }
    
    def _get_recommendation(
        self,
        shadow_score: ShadowScore
    ) -> str:
        """Get recommendation based on shadow scoring."""
        if shadow_score.confidence >= self.shadow_threshold * 1.2:
            return "upweight"  # Stronger than main suggests
        elif shadow_score.confidence >= self.shadow_threshold:
            return "maintain"
        elif shadow_score.confidence >= self.shadow_threshold * 0.7:
            return "downweight"
        else:
            return "exclude"
    
    def get_metrics(self) -> ShadowMetrics:
        """Get current shadow metrics."""
        return self.metrics
    
    def get_feature_insights(self) -> List[Dict[str, Any]]:
        """Get feature insights from shadow scoring."""
        insights = []
        
        for feature, data in self.metrics.feature_performance.items():
            insights.append({
                "feature": feature,
                "avg_score": data["avg_score"],
                "count": data["count"],
                "recommendation": self._get_feature_recommendation(data),
            })
        
        return sorted(insights, key=lambda x: x["avg_score"], reverse=True)
    
    def _get_feature_recommendation(
        self,
        data: Dict[str, float]
    ) -> str:
        """Get recommendation for feature weight."""
        if data["avg_score"] > 1.5:
            return "increase_weight"
        elif data["avg_score"] > 0.8:
            return "maintain_weight"
        elif data["avg_score"] > 0.3:
            return "decrease_weight"
        else:
            return "consider_removing"
    
    def reset_metrics(self) -> None:
        """Reset shadow metrics."""
        self.shadow_history.clear()
        self.metrics = ShadowMetrics()


# Shadow Scoring End