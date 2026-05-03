"""
Probability Calibration - Calibrated Win Rate Estimation.

Calibrates TP/SL probabilities using empirical outcomes
and feature-score buckets.

CRITICAL: Analysis only - no auto-trading.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
import statistics

from config import feature_flags as ff


@dataclass
class CalibrationBucket:
    """Score bucket for probability calibration."""
    
    score_range: tuple = (0.0, 0.0)  # (min, max)
    outcomes: deque = field(default_factory=lambda: deque(maxlen=100))
    wins: int = 0
    losses: int = 0
    
    def add_outcome(self, won: bool) -> None:
        """Add trade outcome."""
        self.outcomes.append(won)
        if won:
            self.wins += 1
        else:
            self.losses += 1
    
    @property
    def total(self) -> int:
        return self.wins + self.losses
    
    @property
    def winrate(self) -> float:
        if self.total == 0:
            return 0.5
        return self.wins / self.total
    
    @property
    def avg_r(self) -> float:
        if not self.outcomes:
            return 0.0
        # Assume 1R for wins, -1R for losses
        return (self.wins - self.losses) / self.total
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "score_range": self.score_range,
            "total": self.total,
            "winrate": self.winrate,
            "avg_r": self.avg_r,
        }


@dataclass
class ProbabilityCalibration:
    """Calibrated probability output."""
    
    score: float = 0.0
    raw_probability: float = 0.5
    calibrated_probability: float = 0.5
    
    # Additional metrics
    sample_size: int = 0
    confidence: float = 0.0
    
    # Per-bucket data
    bucket_winrate: float = 0.5
    bucket_avg_r: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "raw_probability": self.raw_probability,
            "calibrated_probability": self.calibrated_probability,
            "sample_size": self.sample_size,
            "confidence": self.confidence,
            "bucket_winrate": self.bucket_winrate,
            "bucket_avg_r": self.bucket_avg_r,
        }


class ProbabilityCalibrator:
    """Probability calibration engine."""
    
    def __init__(self):
        self.enabled = ff.ENABLE_PROBABILITY_CALIBRATION
        
        # Bucket configuration
        self.bucket_count = 10  # Number of score buckets
        self.bucket_size = 1.0 / self.bucket_count
        
        # Calibration buckets
        self.buckets: List[CalibrationBucket] = []
        
        # Global baseline
        self.global_wins = 0
        self.global_losses = 0
        self.global_outcomes = deque(maxlen=500)
        
        # Min samples for reliable calibration
        self.min_samples = 20
        
        self._init_buckets()
    
    def _init_buckets(self) -> None:
        """Initialize score buckets."""
        for i in range(self.bucket_count):
            min_score = i * self.bucket_size
            max_score = (i + 1) * self.bucket_size
            self.buckets.append(CalibrationBucket(
                score_range=(min_score, max_score)
            ))
    
    def get_bucket_index(self, score: float) -> int:
        """Get bucket index for score."""
        idx = int(score / self.bucket_size)
        return min(idx, self.bucket_count - 1)
    
    def record_outcome(
        self,
        signal_score: float,
        result: str,  # "tp", "sl", "be"
        rr_achieved: float = 0.0
    ) -> None:
        """Record trade outcome for calibration.
        
        Args:
            signal_score: Signal score (0.0-1.0)
            result: Trade result
            rr_achieved: R achieved
        """
        if not self.enabled:
            return
        
        won = result == "tp"
        
        # Record globally
        self.global_outcomes.append(won)
        if won:
            self.global_wins += 1
        else:
            self.global_losses += 1
        
        # Record in bucket
        bucket_idx = self.get_bucket_index(signal_score)
        self.buckets[bucket_idx].add_outcome(won)
    
    def calibrate_probability(
        self,
        signal_score: float,
        raw_probability: float
    ) -> ProbabilityCalibration:
        """Calibrate probability using historical data.
        
        Args:
            signal_score: Signal score (0.0-1.0)
            raw_probability: Raw probability
            
        Returns:
            Calibrated probability with metrics
        """
        calibration = ProbabilityCalibration(
            score=signal_score,
            raw_probability=raw_probability
        )
        
        if not self.enabled:
            calibration.calibrated_probability = raw_probability
            return calibration
        
        # Get bucket
        bucket_idx = self.get_bucket_index(signal_score)
        bucket = self.buckets[bucket_idx]
        
        calibration.sample_size = bucket.total
        calibration.bucket_winrate = bucket.winrate
        calibration.bucket_avg_r = bucket.avg_r
        
        # Calibration confidence based on sample size
        if bucket.total >= 50:
            calibration.confidence = 0.9
        elif bucket.total >= 20:
            calibration.confidence = 0.7
        elif bucket.total >= 10:
            calibration.confidence = 0.5
        else:
            calibration.confidence = 0.3
        
        # Calibrate probability
        if bucket.total >= self.min_samples:
            # Use bucket data
            calibration.calibrated_probability = bucket.winrate
        elif self.global_wins + self.global_losses >= self.min_samples:
            # Fall back to global
            global_wr = self.global_wins / (self.global_wins + self.global_losses)
            
            # Blend with raw based on confidence
            blend = calibration.confidence
            calibration.calibrated_probability = (
                global_wr * blend + raw_probability * (1 - blend)
            )
        else:
            # Not enough data, use raw
            calibration.calibrated_probability = raw_probability
        
        return calibration
    
    def get_bucket_stats(self) -> Dict[int, Dict[str, Any]]:
        """Get statistics per bucket."""
        stats = {}
        
        for i, bucket in enumerate(self.buckets):
            if bucket.total > 0:
                stats[i] = bucket.to_dict()
        
        return stats
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global statistics."""
        total = self.global_wins + self.global_losses
        
        if total == 0:
            return {
                "total": 0,
                "winrate": 0.5,
                "avg_r": 0.0,
            }
        
        return {
            "total": total,
            "winrate": self.global_wins / total,
            "avg_r": (self.global_wins - self.global_losses) / total,
        }
    
    def get_calibrated_probability(
        self,
        signal_score: float
    ) -> float:
        """Get simple calibrated probability."""
        calibration = self.calibrate_probability(signal_score, 0.5)
        return calibration.calibrated_probability
    
    def recalibrate_all(self) -> None:
        """Recalculate all bucket values."""
        # This would be called periodically with fresh data
        pass


# Probability Calibrator End