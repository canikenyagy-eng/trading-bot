"""
Probability Engine - Win Probability Estimation.

This module estimates trade outcome probabilities using historical
performance data and feature reliability weighting.

NOTE: Uses historical data only - no forward-looking predictions.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import statistics

from core.signal_engine import SignalEvaluation, Probabilities
from config import feature_flags as ff


@dataclass
class ProbabilityModel:
    """Historical performance data for probability estimation."""
    
    # Base rates from historical analysis
    base_tp_rate: float = 0.55
    base_sl_rate: float = 0.45
    
    # Reliability adjustments
    historical_confidence: float = 0.5
    
    def get_base_rates(self) -> Tuple[float, float]:
        return self.base_tp_rate, self.base_sl_rate


class ProbabilityEngine:
    """Engine for estimating trade outcome probabilities."""
    
    def __init__(self, model: Optional[ProbabilityModel] = None):
        self.model = model or ProbabilityModel()
        self.enabled = ff.ENABLE_PROBABILITY
        self.min_probability = ff.MIN_PROBABILITY
        
        # Historical data storage
        self._outcome_history: List[Dict] = []
        self._feature_performance: Dict[str, List[bool]] = {}
    
    def calculate_probabilities(
        self,
        signal: SignalEvaluation
    ) -> Probabilities:
        """Calculate outcome probabilities for a signal.
        
        Args:
            signal: SignalEvaluation
            
        Returns:
            Probabilities object
        """
        if not self.enabled:
            return Probabilities()
        
        probabilities = Probabilities()
        
        # Base rates from model
        base_tp, base_sl = self.model.get_base_rates()
        
        # Adjust by confidence (higher confidence = more certain)
        confidence = signal.confidence
        
        # Adjust by regime fit
        regime_adjustment = self._get_regime_adjustment(signal)
        
        # Adjust by features present
        feature_adjustment = self._get_feature_adjustment(signal)
        
        # Calculate adjusted probabilities
        adjusted_tp = base_tp * (1 + (confidence - 0.5) * 0.2) * regime_adjustment * feature_adjustment
        adjusted_tp = max(0.1, min(0.95, adjusted_tp))  # Clamp to reasonable range
        
        probabilities.tp_hit = adjusted_tp
        probabilities.sl_hit = 1.0 - adjusted_tp
        
        # Set confidence in estimate
        probabilities.confidence = min(
            confidence * 1.2,
            1.0
        )
        
        signal.probabilities = probabilities
        
        return probabilities
    
    def _get_regime_adjustment(
        self,
        signal: SignalEvaluation
    ) -> float:
        """Get probability adjustment based on regime."""
        regime = signal.regime.value
        
        # Trending regimes have slightly better odds
        if "trend" in regime:
            return 1.1
        elif regime == "range":
            return 0.9
        elif regime == "volatile":
            return 0.85
        
        return 1.0
    
    def _get_feature_adjustment(
        self,
        signal: SignalEvaluation
    ) -> float:
        """Get probability adjustment based on features."""
        adjustment = 1.0
        feature_count = 0
        
        for name, feature in signal.features.items():
            if feature.present:
                feature_count += 1
                
                # Better features increase probability
                if feature.reliability > 0.7 and feature.strength > 0.7:
                    adjustment += 0.05
                elif feature.reliability > 0.5:
                    adjustment += 0.02
        
        # More features = slightly higher confidence
        if feature_count >= 3:
            adjustment += 0.05
        
        return adjustment
    
    def record_outcome(
        self,
        signal: SignalEvaluation,
        tp_hit: bool,
        rr_achieved: float = 0.0
    ) -> None:
        """Record trade outcome for probability learning.
        
        Args:
            signal: SignalEvaluation
            tp_hit: Whether TP was hit
            rr_achieved: R-multiple achieved
        """
        outcome = {
            "signal_id": signal.signal_id,
            "symbol": signal.symbol,
            "direction": signal.direction.value,
            "tp_hit": tp_hit,
            "rr_achieved": rr_achieved,
            "confidence": signal.confidence,
            "regime": signal.regime.value,
        }
        
        self._outcome_history.append(outcome)
        
        # Track feature performance
        for feature_name in signal.features:
            if feature_name not in self._feature_performance:
                self._feature_performance[feature_name] = []
            
            self._feature_performance[feature_name].append(tp_hit)
    
    def get_feature_winrate(
        self,
        feature_name: str,
        min_samples: int = 10
    ) -> float:
        """Get historical win rate for a feature.
        
        Args:
            feature_name: Name of feature
            min_samples: Minimum samples required
            
        Returns:
            Win rate or 0.5 if insufficient data
        """
        if feature_name not in self._feature_performance:
            return 0.5
        
        results = self._feature_performance[feature_name]
        
        if len(results) < min_samples:
            return 0.5
        
        return statistics.mean(results)
    
    def get_recent_winrate(
        self,
        n: int = 50
    ) -> float:
        """Get win rate from recent trades.
        
        Args:
            n: Number of recent trades
            
        Returns:
            Win rate
        """
        if not self._outcome_history:
            return 0.5
        
        recent = self._outcome_history[-n:]
        if not recent:
            return 0.5
        
        wins = sum(1 for o in recent if o["tp_hit"])
        return wins / len(recent)
    
    def get_symbol_winrate(
        self,
        symbol: str,
        n: int = 50
    ) -> float:
        """Get win rate for a symbol.
        
        Args:
            symbol: Currency symbol
            n: Number of recent trades
            
        Returns:
            Win rate
        """
        symbol_trades = [
            o for o in self._outcome_history[-n:]
            if o["symbol"] == symbol
        ]
        
        if not symbol_trades:
            return 0.5
        
        wins = sum(1 for o in symbol_trades if o["tp_hit"])
        return wins / len(symbol_trades)
    
    def get_regime_winrate(
        self,
        regime: str,
        n: int = 50
    ) -> float:
        """Get win rate for a regime.
        
        Args:
            regime: Regime type
            n: Number of recent trades
            
        Returns:
            Win rate
        """
        regime_trades = [
            o for o in self._outcome_history[-n:]
            if o["regime"] == regime
        ]
        
        if not regime_trades:
            return 0.5
        
        wins = sum(1 for o in regime_trades if o["tp_hit"])
        return wins / len(regime_trades)


# Probability Engine End