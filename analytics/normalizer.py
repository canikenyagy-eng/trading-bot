"""
Feature Normalizer - Statistical Feature Normalization.

Converts feature strengths to statistical percentiles based on
historical distributions.

CRITICAL: Analysis only - no auto-trading.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import deque
import statistics
import math

from config import feature_flags as ff


@dataclass
class FeatureDistribution:
    """Historical distribution for a feature."""
    
    name: str = ""
    values: deque = field(default_factory=lambda: deque(maxlen=1000))
    min_value: float = 0.0
    max_value: float = 1.0
    mean: float = 0.5
    std: float = 0.2
    
    def add_value(self, value: float) -> None:
        """Add value to distribution."""
        self.values.append(value)
        self._recalculate()
    
    def _recalculate(self) -> None:
        """Recalculate distribution stats."""
        if len(self.values) < 2:
            return
        
        self.min_value = min(self.values)
        self.max_value = max(self.values)
        self.mean = statistics.mean(self.values)
        
        if len(self.values) > 1:
            self.std = statistics.stdev(self.values)
    
    def get_percentile(self, value: float) -> float:
        """Get percentile (0.0-1.0) of a value."""
        if len(self.values) < 10:
            return 0.5  # Default to median
        
        # Count how many values are below our value
        below = sum(1 for v in self.values if v < value)
        at = sum(1 for v in self.values if v == value)
        
        percentile = (below + at / 2) / len(self.values)
        
        return max(0.0, min(1.0, percentile))
    
    def get_zscore(self, value: float) -> float:
        """Get z-score of a value."""
        if self.std == 0:
            return 0.0
        
        return (value - self.mean) / self.std
    
    def get_normalized(self, value: float, method: str = "percentile") -> float:
        """Get normalized value."""
        if method == "percentile":
            return self.get_percentile(value)
        elif method == "zscore":
            # Convert z-score to 0-1 range
            z = self.get_zscore(value)
            return 0.5 + (z / 6)  # -3 std = 0, +3 std = 1
        else:
            return (value - self.min_value) / (self.max_value - self.min_value + 1e-10)


@dataclass
class NormalizedFeature:
    """Normalized feature output."""
    
    raw_value: float = 0.0
    normalized_value: float = 0.0
    percentile: float = 0.5
    zscore: float = 0.0
    reliability: float = 0.5
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "percentile": self.percentile,
            "zscore": self.zscore,
            "reliability": self.reliability,
        }


class FeatureNormalizer:
    """Normalizes features using statistical distributions."""
    
    def __init__(self):
        self.enabled = ff.ENABLE_FEATURE_NORMALIZATION
        
        # Initialize distributions
        self.distributions: Dict[str, FeatureDistribution] = {}
        
        # Default min samples required
        self.min_samples = 10
        
        # Normalization method
        self.method = "percentile"  # "percentile", "zscore", "minmax"
        
        self._init_distributions()
    
    def _init_distributions(self) -> None:
        """Initialize feature distributions."""
        features = [
            "fvg_size",
            "fvg_age",
            "ob_strength",
            "ob_age",
            "liquidity_strength",
            "liquidity_distance",
            "displacement",
            "structure_strength",
            "bos_strength",
            "mitigation_strength",
        ]
        
        for name in features:
            self.distributions[name] = FeatureDistribution(name=name)
    
    def normalize(
        self,
        feature_name: str,
        raw_value: float,
        reliability: float = 0.5
    ) -> NormalizedFeature:
        """Normalize a feature value.
        
        Args:
            feature_name: Name of feature
            raw_value: Raw feature value
            reliability: Base reliability (affects normalization confidence)
            
        Returns:
            NormalizedFeature with statistical properties
        """
        if not self.enabled or feature_name not in self.distributions:
            return NormalizedFeature(
                raw_value=raw_value,
                normalized_value=raw_value,
                reliability=reliability
            )
        
        dist = self.distributions[feature_name]
        
        # Get normalized values
        percentile = dist.get_percentile(raw_value)
        zscore = dist.get_zscore(raw_value)
        normalized = dist.get_normalized(raw_value, self.method)
        
        # Calculate reliability (more samples = higher reliability)
        sample_reliability = min(1.0, len(dist.values) / 100)
        reliability = reliability * sample_reliability + (1 - sample_reliability) * 0.5
        
        return NormalizedFeature(
            raw_value=raw_value,
            normalized_value=normalized,
            percentile=percentile,
            zscore=zscore,
            reliability=reliability
        )
    
    def update_distribution(
        self,
        feature_name: str,
        value: float
    ) -> None:
        """Update historical distribution with new value."""
        if not self.enabled or feature_name not in self.distributions:
            return
        
        self.distributions[feature_name].add_value(value)
    
    def update_from_outcome(
        self,
        features: Dict[str, Any],
        result: str  # "tp", "sl", "be"
    ) -> None:
        """Update distributions from trade outcome."""
        if not self.enabled:
            return
        
        for name, value_dict in features.items():
            if isinstance(value_dict, dict):
                raw_value = value_dict.get("strength", value_dict.get("size", 0))
                if raw_value > 0:
                    self.update_distribution(name, raw_value)
    
    def normalize_fvg(
        self,
        fvg_event
    ) -> NormalizedFeature:
        """Normalize FVG feature."""
        if not fvg_event:
            return NormalizedFeature()
        
        # Normalize size
        size_normalized = self.normalize("fvg_size", fvg_event.size)
        
        # Adjust reliability
        reliability = size_normalized.reliability
        
        # Age factor reduces reliability
        if fvg_event.age > 5:
            reliability *= 0.8
        elif fvg_event.age > 10:
            reliability *= 0.6
        
        return NormalizedFeature(
            raw_value=fvg_event.size,
            normalized_value=size_normalized.normalized_value,
            percentile=size_normalized.percentile,
            zscore=size_normalized.zscore,
            reliability=reliability
        )
    
    def normalize_ob(
        self,
        ob_event
    ) -> NormalizedFeature:
        """Normalize Order Block feature."""
        if not ob_event:
            return NormalizedFeature()
        
        strength_normalized = self.normalize("ob_strength", ob_event.strength)
        
        reliability = strength_normalized.reliability
        
        # Touch count increases reliability
        if ob_event.touch_count >= 2:
            reliability *= 1.1
        
        # Age reduces reliability
        if ob_event.age > 10:
            reliability *= 0.8
        
        return NormalizedFeature(
            raw_value=ob_event.strength,
            normalized_value=strength_normalized.normalized_value,
            percentile=strength_normalized.percentile,
            zscore=strength_normalized.zscore,
            reliability=min(1.0, reliability)
        )
    
    def normalize_liquidity(
        self,
        liquidity_pool,
        current_price: float
    ) -> Optional[NormalizedFeature]:
        """Normalize Liquidity feature."""
        if not liquidity_pool:
            return None
        
        # Calculate distance
        if liquidity_pool.direction == "sell_side":
            distance = (liquidity_pool.level - current_price) / current_price
        else:
            distance = (current_price - liquidity_pool.level) / current_price
        
        strength_normalized = self.normalize("liquidity_strength", liquidity_pool.strength)
        distance_normalized = self.normalize("liquidity_distance", distance)
        
        reliability = strength_normalized.reliability * distance_normalized.reliability
        
        return NormalizedFeature(
            raw_value=liquidity_pool.strength,
            normalized_value=strength_normalized.normalized_value * distance_normalized.normalized_value,
            percentile=strength_normalized.percentile * distance_normalized.percentile,
            zscore=strength_normalized.zscore,
            reliability=reliability
        )
    
    def get_distribution_stats(self, feature_name: str) -> Dict[str, float]:
        """Get distribution statistics."""
        if feature_name not in self.distributions:
            return {}
        
        dist = self.distributions[feature_name]
        
        return {
            "count": len(dist.values),
            "mean": dist.mean,
            "std": dist.std,
            "min": dist.min_value,
            "max": dist.max_value,
        }


# Feature Normalizer End