"""
Pattern Discovery - Rule-Based Pattern Detection.

Discovers high-value feature combinations.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque, defaultdict
from datetime import datetime, timedelta


@dataclass
class Pattern:
    """Discovered pattern."""
    
    pattern_id: str
    features: Tuple[str, ...]
    setup_type: str
    
    count: int = 0
    wins: int = 0
    total_rr: float = 0.0
    
    recent_wr: deque = field(default_factory=lambda: deque(maxlen=30))
    
    @property
    def winrate(self) -> float:
        return self.wins / self.count if self.count > 0 else 0.5
    
    @property
    def avg_r(self) -> float:
        return self.total_rr / self.count if self.count > 0 else 0.0
    
    @property
    def edge_score(self) -> float:
        if self.count < 10:
            return 0.0
        return self.winrate * 0.6 + (self.avg_r + 1) / 2 * 0.4
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "features": self.features,
            "setup_type": self.setup_type,
            "count": self.count,
            "winrate": self.winrate,
            "avg_r": self.avg_r,
            "edge_score": self.edge_score,
        }


class PatternDiscovery:
    """Pattern discovery engine."""
    
    def __init__(self):
        self.patterns: Dict[str, Pattern] = {}
        
        # Thresholds
        self.high_value_threshold = 0.60  # 60% winrate
        self.min_pattern_count = 10
        
        # Pattern types
        self.setup_types = [
            "trend_fvg",
            "trend_ob",
            "range_breakout",
            "reversal",
            "momentum",
        ]
    
    def _generate_pattern_id(self, features: Dict[str, Any]) -> str:
        """Generate pattern ID from features."""
        parts = []
        
        for key, value in sorted(features.items()):
            if isinstance(value, dict) and value.get("present"):
                parts.append(key)
        
        return "_".join(parts) if parts else "base"
    
    def _get_setup_type(
        self,
        features: Dict[str, Any],
        regime: str = "trend"
    ) -> str:
        """Determine setup type."""
        if features.get("fvg", {}).get("present"):
            if regime == "trend":
                return "trend_fvg"
            return "momentum"
        
        if features.get("order_block", {}).get("present"):
            return "trend_ob"
        
        if features.get("displacement", {}).get("strength", 0) > 0.7:
            return "range_breakout"
        
        return "base"
    
    def record_trade(
        self,
        features: Dict[str, Any],
        regime: str,
        won: bool,
        rr: float = 0.0
    ) -> None:
        """Record trade for pattern discovery."""
        pattern_id = self._generate_pattern_id(features)
        setup_type = self._get_setup_type(features, regime)
        
        if pattern_id not in self.patterns:
            self.patterns[pattern_id] = Pattern(
                pattern_id=pattern_id,
                features=tuple(sorted(features.keys())),
                setup_type=setup_type
            )
        
        pattern = self.patterns[pattern_id]
        
        pattern.count += 1
        if won:
            pattern.wins += 1
        
        pattern.total_rr += rr
        pattern.recent_wr.append(1.0 if won else 0.0)
    
    def get_high_value_patterns(self) -> List[Dict]:
        """Get high-value patterns."""
        high_value = []
        
        for pattern in self.patterns.values():
            if pattern.count < self.min_pattern_count:
                continue
            
            if pattern.edge_score > self.high_value_threshold:
                high_value.append(pattern.to_dict())
        
        high_value.sort(key=lambda x: x["edge_score"], reverse=True)
        return high_value
    
    def get_all_patterns(self) -> List[Dict]:
        """Get all patterns sorted by edge."""
        all_patterns = [
            p.to_dict() for p in self.patterns.values()
            if p.count >= self.min_pattern_count
        ]
        
        all_patterns.sort(key=lambda x: x["edge_score"], reverse=True)
        return all_patterns
    
    def get_setup_performance(self) -> Dict[str, Dict]:
        """Get performance by setup type."""
        by_setup = defaultdict(lambda: {"count": 0, "wins": 0, "rr": 0.0})
        
        for pattern in self.patterns.values():
            setup = pattern.setup_type
            by_setup[setup]["count"] += pattern.count
            by_setup[setup]["wins"] += pattern.wins
            by_setup[setup]["rr"] += pattern.total_rr
        
        result = {}
        
        for setup, stats in by_setup.items():
            wr = stats["wins"] / stats["count"] if stats["count"] > 0 else 0
            avg_r = stats["rr"] / stats["count"] if stats["count"] > 0 else 0
            
            result[setup] = {
                "count": stats["count"],
                "winrate": wr,
                "avg_r": avg_r,
            }
        
        return result
    
    def get_pattern_report(self) -> Dict[str, Any]:
        """Get pattern discovery report."""
        return {
            "total_patterns": len(self.patterns),
            "high_value_count": len(self.get_high_value_patterns()),
            "setup_performance": self.get_setup_performance(),
            "top_patterns": self.get_all_patterns()[:5],
        }


# Pattern Discovery End