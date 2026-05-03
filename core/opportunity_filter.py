"""
Opportunity Cost Filter - Signal Ranking & Penalty System.

Ranks multiple signals and applies penalties to weaker candidates
based on expected value difference.

CRITICAL: Analysis only - no auto-trading.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from config import feature_flags as ff


@dataclass
class SignalRank:
    """Ranked signal."""
    
    signal: Any
    rank: int = 0
    expected_value: float = 0.0
    penalty: float = 0.0
    adjusted_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "expected_value": self.expected_value,
            "penalty": self.penalty,
            "adjusted_score": self.adjusted_score,
        }


class OpportunityFilter:
    """Opportunity cost filtering."""
    
    def __init__(self):
        self.enabled = ff.ENABLE_OPPORTUNITY_FILTER
        
        # Penalty configuration
        self.rank_penalty_factor = 0.1  # 10% penalty per rank step
        self.min_ev_difference = 0.05  # Min EV diff to apply penalty
        self.max_penalty = 0.3  # Max penalty cap
    
    def rank_signals(
        self,
        signals: List[Any]
    ) -> List[SignalRank]:
        """Rank signals by expected value.
        
        Args:
            signals: List of SignalEvaluation objects
            
        Returns:
            List of SignalRank objects with rankings
        """
        if not self.enabled or not signals:
            return []
        
        # Sort by expected value
        sorted_signals = sorted(
            signals,
            key=lambda s: getattr(s, 'expected_value', 0.0),
            reverse=True
        )
        
        if not sorted_signals:
            return []
        
        # Get top EV
        top_ev = getattr(sorted_signals[0], 'expected_value', 0.0)
        
        # Rank signals
        ranks = []
        for i, signal in enumerate(sorted_signals):
            ev = getattr(signal, 'expected_value', 0.0)
            
            # Calculate penalty based on EV difference
            ev_diff = top_ev - ev
            penalty = self._calculate_penalty(i, ev_diff)
            
            # Calculate adjusted score
            base_score = getattr(signal, 'confidence', 0.5)
            adjusted = base_score * (1 - penalty)
            
            ranks.append(SignalRank(
                signal=signal,
                rank=i + 1,
                expected_value=ev,
                penalty=penalty,
                adjusted_score=adjusted
            ))
        
        return ranks
    
    def _calculate_penalty(
        self,
        rank: int,
        ev_difference: float
    ) -> float:
        """Calculate rank penalty."""
        # Base rank penalty
        rank_penalty = rank * self.rank_penalty_factor
        
        # EV difference penalty
        ev_penalty = 0.0
        if ev_difference > self.min_ev_difference:
            ev_penalty = min(ev_difference * 2, self.max_penalty)
        
        # Combined penalty
        penalty = min(rank_penalty + ev_penalty, self.max_penalty)
        
        return penalty
    
    def filter_signals(
        self,
        signals: List[Any],
        max_count: int = 3,
        min_score: float = 0.3
    ) -> List[Any]:
        """Filter signals by rank and score.
        
        Args:
            signals: List of signals
            max_count: Maximum signals to return
            min_score: Minimum adjusted score
            
        Returns:
            Filtered list of signals
        """
        if not self.enabled:
            return signals[:max_count]
        
        ranks = self.rank_signals(signals)
        
        if not ranks:
            return []
        
        # Filter by rank and score
        filtered = [
            r.signal for r in ranks
            if r.rank <= max_count and r.adjusted_score >= min_score
        ]
        
        return filtered
    
    def get_top_signal(
        self,
        signals: List[Any]
    ) -> Optional[Any]:
        """Get top signal only."""
        if not self.enabled:
            return signals[0] if signals else None
        
        ranks = self.rank_signals(signals)
        
        if not ranks:
            return None
        
        return ranks[0].signal
    
    def get_penalty_report(
        self,
        signals: List[Any]
    ) -> Dict[str, Any]:
        """Get penalty report for signals."""
        ranks = self.rank_signals(signals)
        
        return {
            "total_signals": len(signals),
            "top_ev": ranks[0].expected_value if ranks else 0,
            "penalty_applied": ranks[0].penalty != ranks[-1].penalty if len(ranks) > 1 else False,
            "signals": [r.to_dict() for r in ranks]
        }


# Opportunity Filter End