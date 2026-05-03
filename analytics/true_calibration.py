"""
True Calibration Layer - Empirical Probability Calibration.

Calibrates probabilities using real trading outcomes.
"""

from typing import Dict, List, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque

from config import feature_flags as ff


@dataclass
class ScoreBucket:
    """Score bucket for calibration."""
    
    range_min: float
    range_max: float
    outcomes: deque = field(default_factory=lambda: deque(maxlen=200))
    
    @property
    def count(self) -> int:
        return len(self.outcomes)
    
    @property
    def winrate(self) -> float:
        if not self.outcomes:
            return 0.5
        return sum(1 for o in self.outcomes if o) / len(self.outcomes)
    
    @property
    def avg_rr(self) -> float:
        if not self.outcomes:
            return 0.0
        wins = sum(o for o in self.outcomes if o)
        losses = sum(abs(1 - o) for o in self.outcomes if not o)
        total = len(self.outcomes)
        return (wins - losses) / total


class TrueCalibration:
    """True probability calibration engine."""
    
    def __init__(self):
        self.enabled = ff.ENABLE_TRUE_CALIBRATION
        
        # Bucket configuration
        self.bucket_count = 10
        self.buckets: List[ScoreBucket] = []
        
        self._init_buckets()
    
    def _init_buckets(self) -> None:
        """Initialize score buckets."""
        bucket_size = 1.0 / self.bucket_count
        for i in range(self.bucket_count):
            self.buckets.append(ScoreBucket(
                range_min=i * bucket_size,
                range_max=(i + 1) * bucket_size
            ))
    
    def _get_bucket_index(self, score: float) -> int:
        """Get bucket index for score."""
        idx = int(score / (1.0 / self.bucket_count))
        return min(idx, self.bucket_count - 1)
    
    def record_outcome(self, score: float, won: bool, rr: float = 0.0) -> None:
        """Record outcome for calibration."""
        if not self.enabled:
            return
        
        idx = self._get_bucket_index(score)
        self.buckets[idx].outcomes.append((won, rr))
    
    def get_calibrated_probability(
        self,
        raw_probability: float,
        score: float
    ) -> Dict[str, float]:
        """Get calibrated probability."""
        if not self.enabled:
            return {"raw": raw_probability, "calibrated": raw_probability, "error": 0.0}
        
        idx = self._get_bucket_index(score)
        bucket = self.buckets[idx]
        
        if bucket.count < 10:
            # Not enough data - blend with raw
            blend = min(1.0, bucket.count / 10)
            calibrated = bucket.winrate * blend + raw_probability * (1 - blend)
        else:
            calibrated = bucket.winrate
        
        # Calculate error (Brier score)
        error = abs(calibrated - raw_probability)
        
        return {
            "raw": raw_probability,
            "calibrated": calibrated,
            "error": error,
            "bucket_samples": bucket.count,
            "bucket_winrate": bucket.winrate
        }
    
    def get_calibration_report(self) -> Dict[str, Any]:
        """Get calibration report."""
        if not self.enabled:
            return {"status": "disabled"}
        
        buckets_data = []
        for i, b in enumerate(self.buckets):
            buckets_data.append({
                "range": f"{b.range_min:.1f}-{b.range_max:.1f}",
                "count": b.count,
                "winrate": b.winrate,
                "avg_rr": b.avg_rr
            })
        
        # Calculate overall calibration error
        total_error = 0.0
        for b in self.buckets:
            if b.count > 0:
                # Compare bucket winrate to mid-point
                mid = (b.range_min + b.range_max) / 2
                total_error += abs(b.winrate - mid) * b.count
        
        return {
            "bucket_count": self.bucket_count,
            "total_samples": sum(b.count for b in self.buckets),
            "calibration_error": total_error / max(1, sum(b.count for b in self.buckets)),
            "buckets": buckets_data
        }


# True Calibration End