"""
Final Signal Selection Layer - Signal Ranking & Filtering.

Ranks signals by composite score and keeps only TOP-N per cycle.
Downgrades remaining signals (not hard reject).

CRITICAL: Analysis only - no auto-trading.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from config import feature_flags as ff


@dataclass
class RankedSignal:
    """Ranked signal with composite score."""
    
    signal: Any
    rank: int = 0
    composite_score: float = 0.0
    component_breakdown: Dict[str, float] = field(default_factory=dict)
    reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "composite_score": self.composite_score,
            "component_breakdown": self.component_breakdown,
            "reason": self.reason,
        }


class FinalSelector:
    """Final signal selection layer."""
    
    def __init__(self):
        self.enabled = ff.ENABLE_FINAL_SELECTION
        
        # Configuration
        self.top_n = ff.TOP_N_SIGNALS if hasattr(ff, 'TOP_N_SIGNALS') else 3
        
        # Weights for composite score
        self.ev_weight = 1.0
        self.prob_weight = 1.0
        self.confidence_weight = 1.0
        self.cleanliness_weight = 0.5
    
    def calculate_composite_score(
        self,
        signal,
        path_data: Optional[Dict] = None
    ) -> float:
        """Calculate composite selection score.
        
        Args:
            signal: SignalEvaluation
            path_data: Liquidity path data
            
        Returns:
            Composite score (0-1)
        """
        if not self.enabled:
            return signal.confidence
        
        components = {}
        
        # EV component
        ev = getattr(signal, 'expected_value', 0.0)
        ev_component = self._normalize_ev(ev)
        components['ev'] = ev_component
        
        # Probability component
        probs = getattr(signal, 'probabilities', {})
        tp_prob = probs.get('tp_hit', 0.5)
        components['probability'] = tp_prob
        
        # Confidence component
        conf = getattr(signal, 'confidence', 0.5)
        components['confidence'] = conf
        
        # Cleanliness component (from liquidity path)
        cleanliness = 0.5
        if path_data:
            cleanliness = path_data.get('cleanliness', 0.5)
        components['cleanliness'] = cleanliness
        
        # Calculate weighted composite
        score = (
            ev_component * self.ev_weight +
            tp_prob * self.prob_weight +
            conf * self.confidence_weight +
            cleanliness * self.cleanliness_weight
        ) / (
            self.ev_weight + self.prob_weight + 
            self.confidence_weight + self.cleanliness_weight
        )
        
        return score
    
    def _normalize_ev(self, ev: float) -> float:
        """Normalize EV to 0-1 scale."""
        # EV typically ranges from -0.2 to +0.6
        normalized = (ev + 0.2) / 0.8
        return max(0.0, min(1.0, normalized))
    
    def rank_signals(
        self,
        signals: List[Any],
        path_data: Optional[Dict[str, Dict]] = None
    ) -> List[RankedSignal]:
        """Rank signals by composite score.
        
        Args:
            signals: List of SignalEvaluation
            path_data: Dict of symbol -> liquidity path data
            
        Returns:
            Ranked signals
        """
        if not self.enabled:
            return []
        
        if not signals:
            return []
        
        # Calculate composite scores
        scored = []
        for signal in signals:
            symbol = getattr(signal, 'symbol', 'unknown')
            path = path_data.get(symbol) if path_data else None
            
            score = self.calculate_composite_score(signal, path)
            
            scored.append(RankedSignal(
                signal=signal,
                composite_score=score,
                component_breakdown={}
            ))
        
        # Sort by composite score
        scored.sort(key=lambda x: x.composite_score, reverse=True)
        
        # Assign ranks
        for i, rs in enumerate(scored):
            rs.rank = i + 1
            
            if i < self.top_n:
                rs.reason = "top_selection"
            else:
                rs.reason = "downgraded"
        
        return scored
    
    def select_top_signals(
        self,
        signals: List[Any],
        path_data: Optional[Dict] = None,
        keep_count: Optional[int] = None
    ) -> List[Any]:
        """Select top N signals.
        
        Args:
            signals: List of signals
            path_data: Liquidity path data
            keep_count: Override top_n
            
        Returns:
            Top signals (others downgraded)
        """
        if not self.enabled:
            return signals
        
        ranked = self.rank_signals(path_data=path_data)
        
        if not ranked:
            return signals
        
        limit = keep_count or self.top_n
        
        selected = []
        
        for rs in ranked:
            if rs.rank <= limit:
                # Keep unchanged
                selected.append(rs.signal)
            else:
                # Downgrade but keep in list
                downgraded = rs.signal
                downgraded.downgraded = True
                downgraded.downgrade_reason = rs.reason
                selected.append(downgraded)
        
        return selected
    
    def get_selection_report(
        self,
        signals: List[Any],
        path_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Get selection report."""
        ranked = self.rank_signals(signals, path_data)
        
        if not ranked:
            return {"status": "disabled"}
        
        top = [r for r in ranked if r.rank <= self.top_n]
        downgraded = [r for r in ranked if r.rank > self.top_n]
        
        avg_score = sum(r.composite_score for r in ranked) / len(ranked)
        
        return {
            "total_signals": len(signals),
            "top_n": self.top_n,
            "selected": len(top),
            "downgraded": len(downgraded),
            "average_score": avg_score,
            "top_signals": [
                {"symbol": r.signal.symbol, "score": r.composite_score}
                for r in ranked[:self.top_n]
            ]
        }


# Final Selector End