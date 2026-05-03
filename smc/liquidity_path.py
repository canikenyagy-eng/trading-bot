"""
Liquidity Path Engine - Multi-Target Liquidity Path Modeling.

Tracks and ranks multiple liquidity targets, evaluates path quality,
and models price trajectory to targets.

CRITICAL: Analysis only - no auto-trading.
"""

from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import statistics

from config import feature_flags as ff


@dataclass
class LiquidityTarget:
    """Single liquidity target."""
    
    level: float = 0.0
    pool_type: str = ""
    direction: str = ""
    strength: float = 0.0
    age: int = 0
    touch_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level,
            "pool_type": self.pool_type,
            "direction": self.direction,
            "strength": self.strength,
            "age": self.age,
            "touch_count": self.touch_count,
        }


@dataclass
class LiquidityPath:
    """Liquidity path to target."""
    
    target: LiquidityTarget
    distance_pips: float = 0.0
    distance_pct: float = 0.0
    cleanliness: float = 0.0
    obstacles: int = 0
    consolidation_zones: int = 0
    trajectory_quality: float = 0.0
    path_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target.to_dict(),
            "distance_pips": self.distance_pips,
            "distance_pct": self.distance_pct,
            "cleanliness": self.cleanliness,
            "obstacles": self.obstacles,
            "trajectory_quality": self.trajectory_quality,
            "path_score": self.path_score,
        }


class LiquidityPathEngine:
    """Liquidity path modeling engine."""
    
    def __init__(self):
        self.enabled = ff.ENABLE_LIQUIDITY_PATH
        self.max_targets = 5
        self.max_distance = 200
    
    def find_targets(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        current_price: float,
        direction: str
    ) -> List[LiquidityTarget]:
        """Find all liquidity targets in direction."""
        if not self.enabled:
            return []
        
        targets = []
        
        if direction == "long":
            relevant_highs = [
                (h, i) for i, h in enumerate(highs)
                if h > current_price and h < current_price + self.max_distance * current_price / 10000
            ]
            for h, idx in relevant_highs:
                targets.append(LiquidityTarget(
                    level=h,
                    pool_type="swing_high",
                    direction="sell_side",
                    strength=0.5,
                    age=len(highs) - idx,
                    touch_count=1
                ))
        else:
            relevant_lows = [
                (l, i) for i, l in enumerate(lows)
                if l < current_price and l > current_price - self.max_distance * current_price / 10000
            ]
            for l, idx in relevant_lows:
                targets.append(LiquidityTarget(
                    level=l,
                    pool_type="swing_low",
                    direction="buy_side",
                    strength=0.5,
                    age=len(lows) - idx,
                    touch_count=1
                ))
        
        targets = self._deduplicate_targets(targets)
        targets = self._rank_targets(targets, current_price)
        
        return targets[:self.max_targets]
    
    def _deduplicate_targets(
        self,
        targets: List[LiquidityTarget]
    ) -> List[LiquidityTarget]:
        """Remove duplicate targets."""
        if len(targets) < 2:
            return targets
        
        unique = []
        for t in targets:
            is_duplicate = False
            for u in unique:
                if abs(t.level - u.level) < 0.0005:
                    is_duplicate = True
                    u.touch_count += 1
                    break
            if not is_duplicate:
                unique.append(t)
        
        return unique
    
    def _rank_targets(
        self,
        targets: List[LiquidityTarget],
        current_price: float
    ) -> List[LiquidityTarget]:
        """Rank targets by relevance."""
        for t in targets:
            pips = abs(t.level - current_price) * 10000
            distance_factor = max(0, 1 - pips / 200)
            age_factor = max(0, 1 - t.age / 50)
            touch_factor = min(1, t.touch_count * 0.2)
            
            t.strength = distance_factor * 0.4 + age_factor * 0.3 + touch_factor * 0.3
        
        return sorted(targets, key=lambda t: t.strength, reverse=True)
    
    def evaluate_path(
        self,
        target: LiquidityTarget,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        current_price: float
    ) -> LiquidityPath:
        """Evaluate path quality to target."""
        if not self.enabled or not target:
            return LiquidityPath(target=target, distance_pips=0, path_score=0)
        
        # Distance
        distance = abs(target.level - current_price)
        distance_pips = distance * 10000
        distance_pct = distance / current_price
        
        # Path range
        range_low = min(current_price, target.level)
        range_high = max(current_price, target.level)
        
        # Count consolidation zones
        consolidation_zones = self._count_consolidations(closes, range_low, range_high)
        
        # Count obstacles
        obstacles = self._count_obstacles(highs, lows, range_low, range_high)
        
        # Cleanliness
        cleanliness = 1.0
        if obstacles > 0:
            cleanliness -= obstacles * 0.15
        if consolidation_zones > 0:
            cleanliness -= consolidation_zones * 0.1
        cleanliness = max(0, cleanliness)
        
        # Trajectory quality
        trajectory_quality = self._calculate_trajectory_quality(closes, target.direction)
        
        # Path score
        path_score = (
            cleanliness * 0.4 +
            trajectory_quality * 0.3 +
            target.strength * 0.3
        )
        
        return LiquidityPath(
            target=target,
            distance_pips=distance_pips,
            distance_pct=distance_pct,
            cleanliness=cleanliness,
            obstacles=obstacles,
            consolidation_zones=consolidation_zones,
            trajectory_quality=trajectory_quality,
            path_score=path_score
        )
    
    def _count_consolidations(
        self,
        closes: List[float],
        low: float,
        high: float
    ) -> int:
        """Count consolidation zones in path."""
        count = 0
        in_zone = False
        
        for c in closes:
            if low < c < high:
                if not in_zone:
                    in_zone = True
                    count += 1
            else:
                in_zone = False
        
        return count - 1 if count > 0 else 0
    
    def _count_obstacles(
        self,
        highs: List[float],
        lows: List[float],
        low: float,
        high: float
    ) -> int:
        """Count swing highs/lows in path."""
        count = 0
        
        for h in highs:
            if low < h < high:
                count += 1
        
        for l in lows:
            if low < l < high:
                count += 1
        
        return count
    
    def _calculate_trajectory_quality(
        self,
        closes: List[float],
        direction: str
    ) -> float:
        """Calculate how direct the path is."""
        if len(closes) < 3:
            return 0.5
        
        recent = closes[-10:]
        
        if len(recent) < 2:
            return 0.5
        
        moves = []
        for i in range(1, len(recent)):
            move = (recent[i] - recent[i - 1]) / recent[i - 1]
            moves.append(move)
        
        if not moves:
            return 0.5
        
        variance = statistics.stdev(moves) if len(moves) > 1 else 0
        quality = max(0, 1 - variance * 100)
        
        return quality
    
    def get_best_path(
        self,
        targets: List[LiquidityTarget],
        highs: List[float],
        lows: List[float],
        closes: List[float],
        current_price: float
    ) -> Optional[LiquidityPath]:
        """Get best path to liquidity."""
        if not targets:
            return None
        
        paths = []
        for target in targets:
            path = self.evaluate_path(target, highs, lows, closes, current_price)
            if path.path_score > 0:
                paths.append(path)
        
        if not paths:
            return None
        
        return max(paths, key=lambda p: p.path_score)
    
    def get_path_context(self, path: Optional[LiquidityPath]) -> str:
        """Get textual context for path."""
        if not path:
            return "no_clear_path"
        
        context_parts = []
        
        if path.path_score > 0.7:
            context_parts.append("clear_path")
        elif path.path_score > 0.4:
            context_parts.append("path_ok")
        else:
            context_parts.append("congested_path")
        
        if path.obstacles > 2:
            context_parts.append(f"{path.obstacles}_obstacles")
        
        if path.distance_pips > 100:
            context_parts.append("far_target")
        elif path.distance_pips < 30:
            context_parts.append("near_target")
        
        return ", ".join(context_parts)


# Liquidity Path Engine End