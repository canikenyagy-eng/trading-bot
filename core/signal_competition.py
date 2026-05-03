"""
Signal Competition - Intra-Symbol Competition Handler.

When multiple signals exist for same symbol, keeps best and downgrades others.
"""

from typing import List, Dict, Any
from dataclasses import dataclass

from config import feature_flags as ff


class SignalCompetition:
    """Intra-symbol signal competition handler."""
    
    def __init__(self):
        self.enabled = ff.ENABLE_SIGNAL_COMPETITION
        
        # Keep only best per symbol
        self.keep_best = True
        
        # Degradation factor for others
        self.degradation = 0.3  # 30% score reduction
    
    def resolve_competition(
        self,
        signals: List[Any]
    ) -> List[Any]:
        """Resolve competition between signals of same symbol.
        
        Args:
            signals: List of signals
            
        Returns:
            Resolved signals (best per symbol kept, others degraded)
        """
        if not self.enabled or not signals:
            return signals
        
        # Group by symbol
        by_symbol: Dict[str, List[Any]] = {}
        
        for signal in signals:
            symbol = getattr(signal, 'symbol', 'unknown')
            if symbol not in by_symbol:
                by_symbol[symbol] = []
            by_symbol[symbol].append(signal)
        
        # Resolve each group
        resolved = []
        
        for symbol, group in by_symbol.items():
            if len(group) == 1:
                # Single signal - keep as-is
                resolved.append(group[0])
            else:
                # Multiple signals - keep best
                best = self._select_best(group)
                
                # Add best
                best.is_best = True
                resolved.append(best)
                
                # Add others as degraded
                for signal in group:
                    if signal is not best:
                        signal.is_best = False
                        signal.competition_reason = "downgraded_by_competition"
                        signal.best_score = getattr(best, 'composite_score', best.confidence)
                        signal.score = signal.competition_reason and (getattr(signal, 'composite_score', signal.confidence) * (1 - self.degradation))
                        resolved.append(signal)
        
        return resolved
    
    def _select_best(self, signals: List[Any]) -> Any:
        """Select best signal from group."""
        best = signals[0]
        
        for signal in signals[1:]:
            # Compare by composite score
            best_score = getattr(best, 'composite_score', best.confidence)
            signal_score = getattr(signal, 'composite_score', signal.confidence)
            
            if signal_score > best_score:
                best = signal
        
        return best
    
    def are_conflicting(
        self,
        signal1: Any,
        signal2: Any
    ) -> bool:
        """Check if two signals conflict."""
        if not self.enabled:
            return False
        
        # Same symbol
        if signal1.symbol == signal2.symbol:
            # Same direction = conflict
            if signal1.direction == signal2.direction:
                return True
        
        return False
    
    def get_collision_report(
        self,
        signals: List[Any]
    ) -> Dict[str, Any]:
        """Get collision report."""
        by_symbol: Dict[str, List[str]] = {}
        
        for signal in signals:
            symbol = getattr(signal, 'symbol', 'unknown')
            if symbol not in by_symbol:
                by_symbol[symbol] = []
            by_symbol[symbol].append(signal.direction)
        
        collisions = {
            symbol: len(dirs) for symbol, dirs in by_symbol.items()
            if len(dirs) > 1
        }
        
        return {
            "total_signals": len(signals),
            "symbols": len(by_symbol),
            "collisions": collisions,
            "has_conflicts": len(collisions) > 0
        }


# Signal Competition End