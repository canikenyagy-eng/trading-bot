"""
Feature Interactions - Feature Combination Tracking.

Tracks win rates for feature combinations to identify edge
in combinations rather than individual features.

CRITICAL: Analysis only - no auto-trading.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
import itertools

from config import feature_flags as ff


@dataclass
class InteractionStats:
    """Statistics for feature combination."""
    
    combination: tuple = ()
    wins: int = 0
    losses: int = 0
    
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
        if self.total == 0:
            return 0.0
        # Assumes TP = +1R, SL = -1R
        return (self.wins - self.losses) / self.total
    
    def add_outcome(self, won: bool) -> None:
        if won:
            self.wins += 1
        else:
            self.losses += 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "combination": "+".join(self.combination),
            "total": self.total,
            "winrate": self.winrate,
            "avg_r": self.avg_r,
        }


@dataclass
class FeatureInteractionResult:
    """Feature interaction analysis result."""
    
    combination: tuple = ()
    winrate: float = 0.5
    avg_r: float = 0.0
    sample_size: int = 0
    reliability: float = 0.0
    
    # Comparison
    vs_single_features: float = 0.0  # Win rate delta
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "combination": "+".join(self.combination),
            "winrate": self.winrate,
            "avg_r": self.avg_r,
            "sample_size": self.sample_size,
            "reliability": self.reliability,
            "vs_single": self.vs_single_features,
        }


class FeatureInteractions:
    """Feature interaction tracking."""
    
    def __init__(self):
        self.enabled = ff.ENABLE_FEATURE_INTERACTIONS
        
        # Min samples for reliable stats
        self.min_samples = 5
        
        # Track all interactions
        self.interactions: Dict[tuple, InteractionStats] = {}
        
        # Track single features for comparison
        self.single_stats: Dict[str, InteractionStats] = {}
        
        # Max combination size
        self.max_combo_size = 3
    
    def _get_feature_set(
        self,
        features: Dict[str, Any]
    ) -> tuple:
        """Extract feature set as sorted tuple."""
        active = sorted([
            name for name, value in features.items()
            if isinstance(value, dict) and value.get("present", False)
        ])
        return tuple(active)
    
    def _generate_combinations(
        self,
        features: tuple
    ) -> List[tuple]:
        """Generate all valid combinations."""
        combos = []
        
        # Single features
        for f in features:
            combos.append((f,))
        
        # Pairs
        if len(features) >= 2:
            for combo in itertools.combinations(features, 2):
                combos.append(combo)
        
        # Triplets (if enabled)
        if len(features) >= 3 and self.max_combo_size >= 3:
            for combo in itertools.combinations(features, 3):
                combos.append(combo)
        
        return combos
    
    def record_outcome(
        self,
        features: Dict[str, Any],
        result: str  # "tp", "sl", "be"
    ) -> None:
        """Record trade outcome with features.
        
        Args:
            features: Dict of feature breakdowns
            result: Trade result
        """
        if not self.enabled:
            return
        
        won = result == "tp"
        
        # Get active features
        feature_set = self._get_feature_set(features)
        
        if not feature_set:
            return
        
        # Generate all combinations
        combinations = self._generate_combinations(feature_set)
        
        # Update stats for each combination
        for combo in combinations:
            if combo not in self.interactions:
                self.interactions[combo] = InteractionStats(combination=combo)
            
            self.interactions[combo].add_outcome(won)
        
        # Update single feature stats for comparison
        for feature in feature_set:
            if feature not in self.single_stats:
                self.single_stats[feature] = InteractionStats(combination=(feature,))
            self.single_stats[feature].add_outcome(won)
    
    def get_interaction_stats(
        self,
        features: Dict[str, Any]
    ) -> List[FeatureInteractionResult]:
        """Get interaction stats for features.
        
        Args:
            features: Active feature breakdowns
            
        Returns:
            List of FeatureInteractionResult sorted by winrate
        """
        if not self.enabled:
            return []
        
        feature_set = self._get_feature_set(features)
        
        if not feature_set:
            return []
        
        results = []
        
        # Generate combinations
        combinations = self._generate_combinations(feature_set)
        
        # Calculate baseline (average single feature winrate)
        baseline_wr = 0.5
        if self.single_stats:
            valid = [s.winrate for s in self.single_stats.values() if s.total >= self.min_samples]
            if valid:
                baseline_wr = sum(valid) / len(valid)
        
        # Get stats for each combination
        for combo in combinations:
            if combo not in self.interactions:
                continue
            
            stats = self.interactions[combo]
            
            # Calculate reliability
            reliability = min(1.0, stats.total / 30)
            
            # Calculate vs single features delta
            vs_single = stats.winrate - baseline_wr
            
            results.append(FeatureInteractionResult(
                combination=combo,
                winrate=stats.winrate,
                avg_r=stats.avg_r,
                sample_size=stats.total,
                reliability=reliability,
                vs_single_features=vs_single
            ))
        
        # Sort by winrate
        return sorted(results, key=lambda r: r.winrate, reverse=True)
    
    def get_best_combination(
        self,
        features: Dict[str, Any]
    ) -> Optional[FeatureInteractionResult]:
        """Get best feature combination."""
        results = self.get_interaction_stats(features)
        
        if not results:
            return None
        
        # Filter by reliability and return best
        valid = [r for r in results if r.reliability >= 0.3]
        
        if valid:
            return valid[0]
        
        return results[0]
    
    def get_edge_signals(
        self,
        features: Dict[str, Any]
    ) -> Dict[str, bool]:
        """Get edge signals for each combination.
        
        Returns:
            Dict of combination -> has_edge
        """
        if not self.enabled:
            return {}
        
        results = self.get_interaction_stats(features)
        
        edge_signals = {}
        
        for r in results:
            # Edge = higher than baseline + minimum sample
            has_edge = (
                r.vs_single_features > 0.05 and
                r.sample_size >= self.min_samples
            )
            
            edge_signals["+".join(r.combination)] = has_edge
        
        return edge_signals
    
    def get_top_interactions(
        self,
        min_samples: int = 5,
        min_winrate: float = 0.5,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get top performing interactions.
        
        Args:
            min_samples: Minimum samples
            min_winrate: Minimum winrate
            limit: Max results
            
        Returns:
            List of interaction stats
        """
        if not self.enabled:
            return []
        
        results = []
        
        for combo, stats in self.interactions.items():
            if stats.total >= min_samples and stats.winrate >= min_winrate:
                results.append({
                    **stats.to_dict(),
                    "reliability": min(1.0, stats.total / 30)
                })
        
        # Sort by winrate
        results.sort(key=lambda r: r["winrate"], reverse=True)
        
        return results[:limit]
    
    def get_single_feature_baseline(
        self,
        feature_name: str
    ) -> float:
        """Get single feature baseline winrate."""
        if feature_name not in self.single_stats:
            return 0.5
        
        stats = self.single_stats[feature_name]
        
        if stats.total < self.min_samples:
            return 0.5
        
        return stats.winrate


# Feature Interactions End