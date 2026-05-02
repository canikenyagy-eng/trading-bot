"""
Shadow Live Validation Engine - Real-time Strategy Monitoring.

This module validates trading strategies in real-time by monitoring
signals and outcomes without executing actual trades. It compares
live performance against backtest expectations.

CRITICAL: Live validation only. No real trading execution.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import statistics

from core.signal_engine import SignalEvaluation, Direction
from backtest.validation import BacktestValidationEngine, BacktestValidationResult
from config import feature_flags as ff


@dataclass
class LiveValidationResult:
    """Complete live validation result."""
    
    # Live metrics
    live_signals: int = 0
    live_outcomes: int = 0
    live_winrate: float = 0.0
    live_avg_r: float = 0.0
    
    # Comparison with backtest
    backtest_winrate: float = 0.0
    winrate_delta: float = 0.0
    
    convergence_score: float = 0.0  # 0-1, how close live is to backtest
    
    # Drift detection
    drift_detected: bool = False
    drift_magnitude: float = 0.0
    drift_type: str = ""  # "positive", "negative"
    
    # Confidence adjustments
    new_confidence_multiplier: float = 1.0
    confidence_valid: bool = True
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    
    # Timestamp
    validated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "live_signals": self.live_signals,
            "live_outcomes": self.live_outcomes,
            "live_winrate": self.live_winrate,
            "live_avg_r": self.live_avg_r,
            "backtest_winrate": self.backtest_winrate,
            "winrate_delta": self.winrate_delta,
            "convergence_score": self.convergence_score,
            "drift_detected": self.drift_detected,
            "drift_magnitude": self.drift_magnitude,
            "drift_type": self.drift_type,
            "new_confidence_multiplier": self.new_confidence_multiplier,
            "confidence_valid": self.confidence_valid,
            "recommendations": self.recommendations,
            "validated_at": self.validated_at.isoformat(),
        }


@dataclass
class DriftEvent:
    """Drift detection event."""
    
    timestamp: datetime
    drift_type: str  # "positive", "negative"
    magnitude: float
    cause: str
    
    # Previous vs current
    previous_value: float = 0.0
    current_value: float = 0.0


class ShadowLiveValidationEngine:
    """Engine for live strategy validation.
    
    CRITICAL: Monitoring only. Does NOT execute trades.
    
    This engine:
    1. Monitors live signals (from main flow)
    2. Records outcomes without execution
    3. Compares to backtest historical
    4. Detects regime/performance drift
    5. Calibrates confidence
    """
    
    def __init__(self, backtest_result: Optional[BacktestValidationResult] = None):
        self.backtest_result = backtest_result
        
        # Live tracking (in-memory for now, would be persistent in production)
        self.live_signals: List[SignalEvaluation] = []
        self.live_outcomes: List[Dict] = []
        
        # Parameters
        self.min_live_samples = 10  # Minimum before validation
        self.max_live_samples = 100  # Sliding window
        self.drift_threshold = 0.15  # 15% delta triggers drift
        self.convergence_threshold = 0.70  # 70% convergence needed
        self.calibration_window = 20  # Trades for calibration
        
        # Drift tracking
        self.drift_history: List[DriftEvent] = []
        self._recent_winrates = deque(maxlen=20)
        
        # Current result
        self.current_result: Optional[LiveValidationResult] = None
    
    def set_backtest_reference(
        self,
        backtest_result: BacktestValidationResult
    ) -> None:
        """Set backtest result as reference for live comparison."""
        self.backtest_result = backtest_result
    
    def record_live_signal(
        self,
        signal: SignalEvaluation
    ) -> None:
        """Record a live signal (from main flow).
        
        This does NOT execute the trade - only records for monitoring.
        """
        self.live_signals.append(signal)
        
        # Trim to max window
        if len(self.live_signals) > self.max_live_samples:
            self.live_signals.pop(0)
    
    def record_live_outcome(
        self,
        signal_id: str,
        result: str,  # "tp", "sl", "be"
        rr_achieved: float
    ) -> None:
        """Record a live outcome (without executing).
        
        This is called AFTER trade would have closed.
        """
        # Find signal
        signal = next(
            (s for s in self.live_signals if s.signal_id == signal_id),
            None
        )
        
        if signal is None:
            return
        
        outcome = {
            "signal_id": signal_id,
            "symbol": signal.symbol,
            "direction": signal.direction.value,
            "result": result,
            "rr_achieved": rr_achieved,
            "timestamp": datetime.now().isoformat(),
        }
        
        self.live_outcomes.append(outcome)
        
        # Update rolling win rate
        wins = sum(1 for o in self.live_outcomes[-20:] if o["result"] == "tp")
        winrate = wins / min(len(self.live_outcomes), 20)
        self._recent_winrates.append(winrate)
        
        # Trim to max window
        if len(self.live_outcomes) > self.max_live_samples:
            self.live_outcomes.pop(0)
    
    def validate_live(
        self
    ) -> LiveValidationResult:
        """Validate live performance against backtest reference."""
        result = LiveValidationResult()
        
        if len(self.live_outcomes) < self.min_live_samples:
            result.confidence_valid = False
            result.recommendations.append("insufficient_live_samples")
            self.current_result = result
            return result
        
        # Basic live metrics
        result.live_signals = len(self.live_signals)
        result.live_outcomes = len(self.live_outcomes)
        
        wins = [o for o in self.live_outcomes if o["result"] == "tp"]
        result.live_winrate = len(wins) / len(self.live_outcomes)
        result.live_avg_r = sum(o["rr_achieved"] for o in self.live_outcomes) / len(self.live_outcomes)
        
        # Compare against backtest
        if self.backtest_result:
            result.backtest_winrate = self.backtest_result.win_rate
            result.winrate_delta = result.live_winrate - result.backtest_winrate
            
            # Convergence score
            result.convergence_score = self._calculate_convergence(
                result.live_winrate,
                result.backtest_winrate
            )
        
        # Drift detection
        drift = self._detect_drift()
        result.drift_detected = drift["detected"]
        result.drift_magnitude = drift["magnitude"]
        result.drift_type = drift["type"]
        
        if drift["detected"]:
            result.recommendations.append(f"drift_{drift['type']}")
        
        # Confidence calibration
        calibration = self._calibrate_confidence(result)
        result.new_confidence_multiplier = calibration["multiplier"]
        
        if calibration["action"]:
            result.recommendations.append(calibration["action"])
        
        # Check convergence threshold
        if result.convergence_score < self.convergence_threshold:
            result.confidence_valid = False
            result.recommendations.append("low_convergence")
        
        result.validated_at = datetime.now()
        self.current_result = result
        
        return result
    
    def _calculate_convergence(
        self,
        live_winrate: float,
        backtest_winrate: float
    ) -> float:
        """Calculate convergence score (0-1)."""
        if backtest_winrate == 0:
            return 0.0
        
        # How close is live to backtest?
        ratio = live_winrate / backtest_winrate
        
        # Perfect convergence = 1.0
        # Allow 10% variance = 0.9
        if ratio >= 0.9 and ratio <= 1.1:
            return 1.0
        elif ratio >= 0.8 and ratio <= 1.2:
            return 0.8
        elif ratio >= 0.7 and ratio <= 1.3:
            return 0.6
        elif ratio >= 0.6 and ratio <= 1.4:
            return 0.4
        elif ratio >= 0.5 and ratio <= 1.5:
            return 0.2
        else:
            return 0.0
    
    def _detect_drift(self) -> Dict[str, Any]:
        """Detect performance drift."""
        if len(self._recent_winrates) < 2:
            return {"detected": False, "magnitude": 0.0, "type": ""}
        
        # Compare recent performance to earlier
        recent = list(self._recent_winrates)
        mid_point = len(recent) // 2
        
        early = recent[:mid_point]
        late = recent[mid_point:]
        
        if not early or not late:
            return {"detected": False, "magnitude": 0.0, "type": ""}
        
        early_wr = statistics.mean(early)
        late_wr = statistics.mean(late)
        
        delta = late_wr - early_wr
        
        # Check threshold
        if abs(delta) < self.drift_threshold:
            return {"detected": False, "magnitude": abs(delta), "type": ""}
        
        drift_type = "positive" if delta > 0 else "negative"
        
        # Record drift event
        self.drift_history.append(DriftEvent(
            timestamp=datetime.now(),
            drift_type=drift_type,
            magnitude=abs(delta),
            cause="winrate_shift",
            previous_value=early_wr,
            current_value=late_wr,
        ))
        
        return {
            "detected": True,
            "magnitude": abs(delta),
            "type": drift_type,
        }
    
    def _calibrate_confidence(
        self,
        result: LiveValidationResult
    ) -> Dict[str, Any]:
        """Calculate confidence calibration multiplier."""
        calibration = {"multiplier": 1.0, "action": ""}
        
        if result.drift_detected:
            # Negative drift = reduce confidence
            if result.drift_type == "negative":
                # Reduced by drift magnitude
                calibration["multiplier"] = max(0.5, 1.0 - result.drift_magnitude * 2)
                calibration["action"] = "reduce_confidence"
            
            # Positive drift = slightly increase
            elif result.drift_type == "positive":
                calibration["multiplier"] = min(1.2, 1.0 + result.drift_magnitude)
                calibration["action"] = "increase_confidence"
        
        # Check convergence
        if result.convergence_score > 0.9:
            calibration["multiplier"] = 1.0  # Perfect match
            calibration["action"] = "maintain_confidence"
        elif result.convergence_score < 0.6:
            calibration["multiplier"] *= 0.8  # Reduce
            calibration["action"] = "reduce_confidence_due_to_divergence"
        
        return calibration
    
    def get_recent_performance(
        self,
        n: int = 10
    ) -> Dict[str, float]:
        """Get recent performance metrics."""
        if not self.live_outcomes:
            return {
                "win_rate": 0.0,
                "avg_r": 0.0,
                "count": 0,
            }
        
        recent = self.live_outcomes[-n:]
        
        if not recent:
            return {
                "win_rate": 0.0,
                "avg_r": 0.0,
                "count": 0,
            }
        
        wins = sum(1 for o in recent if o["result"] == "tp")
        
        return {
            "win_rate": wins / len(recent),
            "avg_r": sum(o["rr_achieved"] for o in recent) / len(recent),
            "count": len(recent),
            "convergence": self.current_result.convergence_score if self.current_result else 0.0,
        }
    
    def get_drift_history(
        self
    ) -> List[Dict[str, Any]]:
        """Get drift history."""
        return [
            {
                "timestamp": d.timestamp.isoformat(),
                "type": d.drift_type,
                "magnitude": d.magnitude,
                "cause": d.cause,
            }
            for d in self.drift_history
        ]
    
    def get_validation_summary(
        self
    ) -> str:
        """Get human-readable validation summary."""
        if not self.current_result:
            return "No live validation result yet"
        
        result = self.current_result
        
        lines = [
            "=== Shadow Live Validation ===",
            f"Live Signals: {result.live_signals}",
            f"Live Outcomes: {result.live_outcomes}",
            f"Live Win Rate: {result.live_winrate:.1%}",
            f"Backtest Win Rate: {result.backtest_winrate:.1%}",
            f"Win Rate Delta: {result.winrate_delta:+.1%}",
            f"Convergence: {result.convergence_score:.2f}",
            f"Drift Detected: {result.drift_detected} ({result.drift_type})",
            f"Confidence Valid: {result.confidence_valid}",
            f"Multiplier: {result.new_confidence_multiplier:.2f}",
        ]
        
        if result.recommendations:
            lines.append("")
            lines.append("Recommendations:")
            for rec in result.recommendations:
                lines.append(f"  - {rec}")
        
        return "\n".join(lines)


# Shadow Live Validation End