"""
Feature Ablation Test - Identify Feature Contribution.

Tests system performance with/without specific features.
"""

from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class AblationResult:
    """Ablation test result."""
    
    feature: str
    with_feature: Dict[str, float]
    without_feature: Dict[str, float]
    contribution: float  # Difference
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature": self.feature,
            "with_feature": self.with_feature,
            "without_feature": self.without_feature,
            "contribution": self.contribution,
        }


class FeatureAblationTest:
    """Feature ablation testing."""
    
    def __init__(self):
        self.enabled = True
        
        # Features to test
        self.features_to_test = [
            "fvg",
            "order_block",
            "liquidity",
            "displacement",
            "liquidity_path",
            "mitigation"
        ]
    
    def filter_by_feature(
        self,
        trades: List[Dict],
        feature: str,
        has_feature: bool
    ) -> List[Dict]:
        """Filter trades by feature presence."""
        filtered = []
        
        for trade in trades:
            features = trade.get("features", {})
            has = feature in features and features[feature].get("present", False)
            
            if has == has_feature:
                filtered.append(trade)
        
        return filtered
    
    def calculate_metrics(self, trades: List[Dict]) -> Dict[str, float]:
        """Calculate metrics from trades."""
        if not trades:
            return {"wr": 0, "pf": 0, "avg_r": 0}
        
        wins = sum(1 for t in trades if t.get("result") == "tp")
        total = len(trades)
        
        wr = wins / total if total > 0 else 0
        
        rr = [t.get("rr", 0) for t in trades]
        avg_r = sum(rr) / len(rr) if rr else 0
        
        gross_profit = sum(r for r in rr if r > 0)
        gross_loss = abs(sum(r for r in rr if r < 0))
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        
        return {
            "win_rate": wr,
            "profit_factor": pf,
            "avg_r": avg_r,
            "trade_count": total,
        }
    
    def run_ablation(
        self,
        trades: List[Dict],
        feature: str
    ) -> AblationResult:
        """Run ablation test for feature."""
        # With feature
        with_feature = self.filter_by_feature(trades, feature, True)
        with_metrics = self.calculate_metrics(with_feature)
        
        # Without feature
        without_feature = self.filter_by_feature(trades, feature, False)
        without_metrics = self.calculate_metrics(without_feature)
        
        # Calculate contribution (difference in avg_r)
        contribution = with_metrics.get("avg_r", 0) - without_metrics.get("avg_r", 0)
        
        return AblationResult(
            feature=feature,
            with_feature=with_metrics,
            without_feature=without_metrics,
            contribution=contribution
        )
    
    def run_full_analysis(
        self,
        trades: List[Dict]
    ) -> Dict[str, AblationResult]:
        """Run ablation for all features."""
        results = {}
        
        for feature in self.features_to_test:
            results[feature] = self.run_ablation(trades, feature)
        
        return results
    
    def get_feature_ranking(
        self,
        results: Dict[str, AblationResult]
    ) -> List[Dict[str, Any]]:
        """Rank features by contribution."""
        ranking = []
        
        for feature, result in results.items():
            ranking.append({
                "feature": feature,
                "contribution": result.contribution,
                "with_wr": result.with_feature.get("win_rate", 0),
                "without_wr": result.without_feature.get("win_rate", 0),
                "with_pf": result.with_feature.get("profit_factor", 0),
                "without_pf": result.without_feature.get("profit_factor", 0),
            })
        
        # Sort by contribution
        ranking.sort(key=lambda x: x["contribution"], reverse=True)
        
        return ranking


# Feature Ablation Test End