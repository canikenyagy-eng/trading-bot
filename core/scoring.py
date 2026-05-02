"""
Scoring Engine - Component Scoring for Signal Evaluation.

This module calculates individual feature scores and combines them
into a total signal score using weighted reliability.

Scoring Formula: score = Σ(feature_score × weight × reliability)
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from core.signal_engine import (
    SignalEvaluation, ScoreComponent, FeatureBreakdown, Direction
)
from config import feature_flags as ff


@dataclass
class ScoringWeights:
    """Configurable scoring weights for each feature."""
    
    structure: float = 1.5
    liquidity: float = 1.2
    fvg: float = 1.0
    order_block: float = 1.3
    mitigation: float = 1.1
    regime_fit: float = 0.8
    entry_quality: float = 1.0
    smt: float = 0.7
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "structure": self.structure,
            "liquidity": self.liquidity,
            "fvg": self.fvg,
            "order_block": self.order_block,
            "mitigation": self.mitigation,
            "regime_fit": self.regime_fit,
            "entry_quality": self.entry_quality,
            "smt": self.smt,
        }
    
    def get(self, feature: str) -> float:
        """Get weight for a feature."""
        return getattr(self, feature, 1.0)


class ScoringEngine:
    """Engine for calculating signal scores."""
    
    def __init__(self, weights: Optional[ScoringWeights] = None):
        self.weights = weights or ScoringWeights()
        self.adaptive_enabled = ff.ENABLE_META_ADAPTATION
        self._historical_scores: List[Dict] = []
    
    def calculate_signal_score(
        self, 
        signal: SignalEvaluation
    ) -> float:
        """Calculate total weighted score for a signal.
        
        Args:
            signal: SignalEvaluation to score
            
        Returns:
            Total weighted score
        """
        total = 0.0
        
        for feature_name, feature_data in signal.features.items():
            if not feature_data.present:
                continue
            
            # Get weight for this feature
            weight = self.weights.get(feature_name)
            
            # Create score component
            component = ScoreComponent(
                feature=feature_name,
                raw_score=feature_data.strength,
                weight=weight,
                reliability=feature_data.reliability,
                component_details={
                    "age": feature_data.age,
                    "filled": feature_data.filled,
                }
            )
            
            total += component.weighted_score
            signal.add_score_component(component)
        
        return total
    
    def score_feature_strength(
        self,
        feature: FeatureBreakdown,
        feature_name: str
    ) -> float:
        """Score an individual feature's strength.
        
        Args:
            feature: FeatureBreakdown data
            feature_name: Name of feature
            
        Returns:
            Feature score (0.0 to 2.0 typically)
        """
        if not feature.present:
            return 0.0
        
        score = 0.0
        
        # Base strength
        score += feature.strength
        
        # Recency bonus (recent features worth more)
        if feature.age <= 3:
            score += 0.3
        elif feature.age <= 5:
            score += 0.1
        
        # Not filled bonus
        if not feature.filled:
            score += 0.2
        
        # Reliability weighting
        score *= (0.5 + feature.reliability * 0.5)
        
        return min(score, 2.0)  # Cap at 2.0
    
    def score_structure(
        self,
        signal: SignalEvaluation
    ) -> float:
        """Score BOS/CHOCH structure.
        
        Args:
            signal: SignalEvaluation with structure features
            
        Returns:
            Structure score
        """
        feature = signal.features.get("structure")
        if not feature or not feature.present:
            return 0.0
        
        return self.score_feature_strength(feature, "structure")
    
    def score_fvg(
        self,
        signal: SignalEvaluation
    ) -> float:
        """Score Fair Value Gap presence.
        
        Args:
            signal: SignalEvaluation with FVG features
            
        Returns:
            FVG score
        """
        if not ff.ENABLE_FVG:
            return 0.0
        
        feature = signal.features.get("fvg")
        if not feature or not feature.present:
            return 0.0
        
        return self.score_feature_strength(feature, "fvg")
    
    def score_order_block(
        self,
        signal: SignalEvaluation
    ) -> float:
        """Score Order Block presence.
        
        Args:
            signal: SignalEvaluation with OB features
            
        Returns:
            Order Block score
        """
        if not ff.ENABLE_OB:
            return 0.0
        
        feature = signal.features.get("order_block")
        if not feature or not feature.present:
            return 0.0
        
        return self.score_feature_strength(feature, "order_block")
    
    def score_liquidity(
        self,
        signal: SignalEvaluation
    ) -> float:
        """Score liquidity pool alignment.
        
        Args:
            signal: SignalEvaluation with liquidity features
            
        Returns:
            Liquidity score
        """
        if not ff.ENABLE_LIQUIDITY:
            return 0.0
        
        feature = signal.features.get("liquidity")
        if not feature or not feature.present:
            return 0.0
        
        return self.score_feature_strength(feature, "liquidity")
    
    def score_smt(
        self,
        signal: SignalEvaluation
    ) -> float:
        """Score SMT (Smart Money Tracker) alignment.
        
        Args:
            signal: SignalEvaluation with SMT features
            
        Returns:
            SMT score
        """
        if not ff.ENABLE_SMT:
            return 0.0
        
        feature = signal.features.get("smt")
        if not feature or not feature.present:
            return 0.0
        
        return self.score_feature_strength(feature, "smt")
    
    def score_mitigation(
        self,
        signal: SignalEvaluation
    ) -> float:
        """Score mitigation zone quality.
        
        Args:
            signal: SignalEvaluation with mitigation features
            
        Returns:
            Mitigation score
        """
        if not ff.ENABLE_MITIGATION:
            return 0.0
        
        feature = signal.features.get("mitigation")
        if not feature or not feature.present:
            return 0.0
        
        return self.score_feature_strength(feature, "mitigation")
    
    def score_regime_fit(
        self,
        signal: SignalEvaluation
    ) -> float:
        """Score how well setup fits market regime.
        
        Args:
            signal: SignalEvaluation with regime data
            
        Returns:
            Regime fit score
        """
        if not ff.ENABLE_REGIME:
            return 0.0
        
        # Check regime alignment with direction
        regime = signal.regime
        direction = signal.direction
        
        # Trend in direction of trade
        if regime.value == "trend_up" and direction == Direction.LONG:
            return 1.2
        elif regime.value == "trend_down" and direction == Direction.SHORT:
            return 1.2
        # Range - reduced score
        elif regime.value == "range":
            return 0.7
        # Volatile - caution
        elif regime.value == "volatile":
            return 0.5
        
        return 0.3  # Unknown regime
    
    def calculate_confidence_components(
        self,
        signal: SignalEvaluation
    ) -> Dict[str, float]:
        """Calculate confidence breakdown by component.
        
        Args:
            signal: SignalEvaluation
            
        Returns:
            Dictionary of confidence components
        """
        from core.signal_engine import ConfidenceComponents
        
        components = ConfidenceComponents()
        
        # Structure confidence
        structure_score = self.score_structure(signal)
        components.structure = min(structure_score / 2.0, 1.0)
        
        # Liquidity confidence
        liquidity_score = self.score_liquidity(signal)
        components.liquidity = min(liquidity_score / 2.0, 1.0)
        
        # Entry quality - based on FVG/OB/Mitigation
        entry_score = (
            self.score_fvg(signal) +
            self.score_order_block(signal) +
            self.score_mitigation(signal)
        ) / 3.0
        components.entry_quality = min(entry_score / 2.0, 1.0)
        
        # Regime fit
        regime_score = self.score_regime_fit(signal)
        components.regime_fit = min(regime_score / 1.5, 1.0)
        
        return components
    
    def calculate_total_score(
        self,
        signal: SignalEvaluation
    ) -> float:
        """Calculate total signal score from all components.
        
        Args:
            signal: SignalEvaluation
            
        Returns:
            Total score
        """
        score = 0.0
        
        # Score each feature category
        score += self.score_structure(signal) * self.weights.structure
        score += self.score_liquidity(signal) * self.weights.liquidity
        score += self.score_fvg(signal) * self.weights.fvg
        score += self.score_order_block(signal) * self.weights.order_block
        score += self.score_mitigation(signal) * self.weights.mitigation
        score += self.score_regime_fit(signal) * self.weights.regime_fit
        score += self.score_smt(signal) * self.weights.smt
        
        return score
    
    def get_score_breakdown(
        self,
        signal: SignalEvaluation
    ) -> Dict[str, float]:
        """Get detailed score breakdown by component.
        
        Args:
            signal: SignalEvaluation
            
        Returns:
            Dictionary of component scores
        """
        return {
            "structure": self.score_structure(signal),
            "liquidity": self.score_liquidity(signal),
            "fvg": self.score_fvg(signal),
            "order_block": self.score_order_block(signal),
            "mitigation": self.score_mitigation(signal),
            "regime_fit": self.score_regime_fit(signal),
            "smt": self.score_smt(signal),
            "total": self.calculate_total_score(signal),
        }
    
    def adapt_weights(
        self,
        winrate: float,
        feature_name: str
    ) -> None:
        """Adapt weights based on performance.
        
        Args:
            winrate: Recent winrate for feature
            feature_name: Name of feature to adapt
        """
        if not self.adaptive_enabled:
            return
        
        current_weight = self.weights.get(feature_name)
        
        if winrate > 0.55:
            # Good performance - increase weight
            new_weight = min(current_weight * 1.1, 3.0)
        elif winrate < 0.40:
            # Poor performance - decrease weight
            new_weight = max(current_weight * 0.9, 0.3)
        else:
            return
        
        setattr(self.weights, feature_name, new_weight)


# Scoring Engine End