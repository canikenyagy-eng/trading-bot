"""
Signal Clustering - Cluster Similar Signals.

Groups signals by market context and keeps best per cluster.
"""

from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field
import hashlib

from config import feature_flags as ff


@dataclass
class SignalCluster:
    """Signal cluster."""
    
    cluster_id: str
    signals: List[Any] = field(default_factory=list)
    
    @property
    def best_signal(self) -> Any:
        if not self.signals:
            return None
        
        return max(self.signals, 
                key=lambda s: getattr(s, 'composite_score', 
                                getattr(s, 'confidence', 0)))
    
    @property
    def count(self) -> int:
        return len(self.signals)


class SignalClustering:
    """Signal clustering engine."""
    
    def __init__(self):
        self.enabled = ff.ENABLE_SIGNAL_CLUSTERING
        
        # Clustering fields
        self.cluster_by_symbol = True
        self.cluster_by_direction = True
        self.cluster_by_structure = True
    
    def _generate_cluster_id(self, signal) -> str:
        """Generate cluster ID for signal."""
        parts = []
        
        # Symbol
        if self.cluster_by_symbol:
            parts.append(getattr(signal, 'symbol', 'unknown'))
        
        # Direction
        if self.cluster_by_direction:
            parts.append(getattr(signal, 'direction', 'unknown'))
        
        # Structure (for same market idea)
        if self.cluster_by_structure:
            structure = getattr(signal, 'details', {}).get('structure_state', 'unknown')
            # Also include liquidity target if close
            details = signal.details if hasattr(signal, 'details') else {}
            liq = details.get('liquidity_context', 'unknown')[:10] if details else 'none'
            
            parts.append(f"{structure}_{liq}")
        
        # Hash
        combined = "_".join(parts)
        return hashlib.md5(combined.encode()).hexdigest()[:8]
    
    def cluster_signals(
        self,
        signals: List[Any]
    ) -> Dict[str, SignalCluster]:
        """Cluster signals by market context."""
        if not self.enabled or not signals:
            return {}
        
        clusters: Dict[str, SignalCluster] = {}
        
        for signal in signals:
            cluster_id = self._generate_cluster_id(signal)
            
            if cluster_id not in clusters:
                clusters[cluster_id] = SignalCluster(cluster_id=cluster_id)
            
            clusters[cluster_id].signals.append(signal)
        
        return clusters
    
    def resolve_clusters(
        self,
        signals: List[Any]
    ) -> List[Any]:
        """Resolve signals - keep only best per cluster."""
        clusters = self.cluster_signals(signals)
        
        if not clusters:
            return signals
        
        resolved = []
        
        for cluster in clusters.values():
            best = cluster.best_signal
            if best:
                # Mark as cluster winner
                best.is_cluster_winner = True
                best.cluster_id = cluster.cluster_id
                resolved.append(best)
                
                # Downgrade others
                for sig in cluster.signals:
                    if sig is not best:
                        sig.is_cluster_winner = False
                        sig.cluster_id = cluster.cluster_id
                        sig.cluster_reason = "downgraded_by_cluster"
                        resolved.append(sig)
        
        return resolved
    
    def get_cluster_report(
        self,
        signals: List[Any]
    ) -> Dict[str, Any]:
        """Get clustering report."""
        clusters = self.cluster_signals(signals)
        
        cluster_data = {
            cid: {"count": c.count, "best": c.best_signal.symbol if c.best_signal else None}
            for cid, c in clusters.items()
        }
        
        multi_signal = sum(1 for c in clusters.values() if c.count > 1)
        
        return {
            "total_signals": len(signals),
            "total_clusters": len(clusters),
            "multi_signal": multi_signal,
            "clusters": cluster_data
        }


# Signal Clustering End