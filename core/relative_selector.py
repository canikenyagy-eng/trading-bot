"""
Relative Selection - Compare Signals to Best in Batch.

Penalizes signals that are much weaker than the best in the batch.
"""

from typing import Dict, List, Any
from dataclasses import dataclass

from config import feature_flags as ff


@dataclass
class RelativeSelectionResult:
    """Relative selection result."""
    
    rank: int
    relative_score: float
    relative_to_best: float  # Score relative to batch best


class RelativeSelector:
    """Relative signal selector."""
    
    def __init__(self):
        self.enabled = ff.ENABLE_RELATIVE_SELECTION
        
        # Thresholds
        self.min_relative_score = 0.5  # Keep if > 50% of best
        self.penalty_factor = 0.85
    
    def rank_signals(
        self,
        signals: List[Any]
    ) -> List[RelativeSelectionResult]:
        """Rank signals relative to best."""
        if not self.enabled or not signals:
            return []
        
        # Get scores
        scores = []
        for signal in signals:
            score = getattr(signal, 'composite_score', 
                        getattr(signal, 'confidence', 0))
            scores.append((signal, score))
        
        # Find best
        best_score = max(s for _, s in scores)
        
        # Rank
        ranked = []
        for i, (signal, score) in enumerate(sorted(scores, 
                                           key=lambda x: x[1], 
                                           reverse=True)):
            relative = score / best_score if best_score > 0 else 0
            
            ranked.append(RelativeSelectionResult(
                rank=i + 1,
                relative_score=relative,
                relative_to_best=score
            ))
        
        return ranked
    
    def apply_relative_penalty(
        self,
        signals: List[Any]
    ) -> List[Any]:
        """Apply relative selection penalty."""
        if not self.enabled:
            return signals
        
        ranked = self.rank_signals(signals)
        
        if not ranked:
            return signals
        
        # Mark each signal
        for i, result in enumerate(ranked):
            signal = signals[i]
            signal.relative_rank = result.rank
            signal.relative_score = result.relative_score
            
            # Apply penalty for weak signals
            if result.relative_score < self.min_relative_score:
                # Downgrade
                current = getattr(signal, 'composite_score', signal.confidence)
                signal.composite_score = current * self.penalty_factor
                signal.relative_penalty = True
            else:
                signal.relative_penalty = False
        
        return signals
    
    def get_best_in_batch(
        self,
        signals: List[Any]
    ) -> Any:
        """Get absolute best signal in batch."""
        if not signals:
            return None
        
        return max(signals, 
                 key=lambda s: getattr(s, 'composite_score',
                                  getattr(s, 'confidence', 0)))
    
    def get_selection_report(
        self,
        signals: List[Any]
    ) -> Dict[str, Any]:
        """Get relative selection report."""
        ranked = self.rank_signals(signals)
        
        if not ranked:
            return {"status": "disabled"}
        
        weak_signals = sum(1 for r in ranked 
                      if r.relative_score < self.min_relative_score)
        
        avg_relative = sum(r.relative_score for r in ranked) / len(ranked)
        
        return {
            "total_signals": len(signals),
            "strong_signals": len(signals) - weak_signals,
            "weak_signals": weak_signals,
            "average_relative": avg_relative,
            "best_score": max(r.relative_to_best for r in ranked),
            "threshold": self.min_relative_score
        }


# Relative Selector End