"""
Feature Edge Weighting - Analytics-Based Weight Adjustment.

Uses historical win rates to adjust feature weights.
Pulls data from feature_stats.
"""

from typing import Dict, Any
from dataclasses import dataclass

from config import feature_flags as ff


@dataclass
class FeatureEdge:
    """Feature edge calculation."""
    
    feature: str
    winrate: float = 0.5
    avg_r: float = 0.0
    edge_score: float = 0.5
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature": self.feature,
            "winrate": self.winrate,
            "avg_r": self.avg_r,
            "edge_score": self.edge_score,
        }


class FeatureEdgeWeighter:
    """Feature edge weighting engine."""
    
    def __init__(self):
        self.enabled = ff.ENABLE_FEATURE_EDGE_WEIGHTING
        
        # Feature edge cache
        self.feature_edges: Dict[str, FeatureEdge] = {}
        
        # Adaptation
        self.adaptation_strength = 0.3
        self.min_samples = 10
        
        # Base weights
        self.base_weights = dict(ff.DEFAULT_WEIGHTS)
    
    def update_from_analytics(self, feature_stats: Dict[str, Any]) -> None:
        """Update edge from analytics.
        
        Args:
            feature_stats: Dict of feature -> {winrate, avg_r, count}
        """
        if not self.enabled:
            return
        
        for feature, stats in feature_stats.items():
            count = stats.get('count', 0)
            if count < self.min_samples:
                continue
            
            winrate = stats.get('winrate', 0.5)
            avg_r = stats.get('avg_r', 0.0)
            
            # Edge score: combination of winrate and avg_r
            edge_score = (winrate * 0.6 + (avg_r + 1) / 2 * 0.4)
            edge_score = max(0.0, min(1.0, edge_score))
            
            self.feature_edges[feature] = FeatureEdge(
                feature=feature,
                winrate=winrate,
                avg_r=avg_r,
                edge_score=edge_score
            )
    
    def get_edge_weight(self, feature: str, base_weight: float = 1.0) -> float:
        """Get edge-adjusted weight.
        
        Args:
            feature: Feature name
            base_weight: Base weight
            
        Returns:
            Adjusted weight
        """
        if not self.enabled:
            return base_weight
        
        if feature not in self.feature_edges:
            return base_weight
        
        edge = self.feature_edges[feature]
        
        # Calculate adjustment
        edge_delta = edge.edge_score - 0.5  # 0 = baseline, positive = good
        adjustment = edge_delta * self.adaptation_strength
        
        return base_weight * (1 + adjustment)
    
    def get_all_edge_weights(self) -> Dict[str, float]:
        """Get all edge-adjusted weights."""
        weights = {}
        
        for feature, base_weight in self.base_weights.items():
            weights[feature] = self.get_edge_weight(feature, base_weight)
        
        return weights
    
    def get_feature_edges(self) -> Dict[str, Dict]:
        """Get all feature edges."""
        return {
            name: edge.to_dict()
            for name, edge in self.feature_edges.items()
        }
    
    def is_strong_feature(self, feature: str) -> bool:
        """Check if feature is strong."""
        if feature not in self.feature_edges:
            return False
        
        return self.feature_edges[feature].edge_score > 0.6


# Feature Edge Weighter End