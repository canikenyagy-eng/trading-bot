"""
Price Proximity Model - Dynamic Entry Timing.

Optimizes entry timing based on price distance.
"""

from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class ProximityMetrics:
    """Proximity calculation metrics."""
    
    distance: float  # Percentage
    proximity_zone: str  # "hot", "warm", "cold"
    boost_factor: float
    is_actionable: bool


class PriceProximityModel:
    """Price proximity model."""
    
    def __init__(self):
        # Proximity zones (percentage)
        self.hot_zone = 0.001  # 0.1% - very close
        self.warm_zone = 0.005  # 0.5% - close
        self.cold_zone = 0.010  # 1.0% - too far
        
        # Boost/penalty factors
        self.hot_boost = 1.3
        self.warm_boost = 1.1
        self.cold_penalty = 0.7
        
        # Time-based adjustment
        self.enable_time_decay = True
    
    def calculate_proximity(
        self,
        current_price: float,
        entry_price: float
    ) -> ProximityMetrics:
        """Calculate proximity metrics."""
        if not current_price or not entry_price:
            return ProximityMetrics(
                distance=0,
                proximity_zone="cold",
                boost_factor=1.0,
                is_actionable=False
            )
        
        # Calculate distance percentage
        distance = abs(current_price - entry_price) / entry_price
        
        # Determine zone
        if distance <= self.hot_zone:
            zone = "hot"
            boost = self.hot_boost
            actionable = True
        elif distance <= self.warm_zone:
            zone = "warm"
            boost = self.warm_boost
            actionable = True
        elif distance <= self.cold_zone:
            zone = "cold"
            boost = self.cold_penalty
            actionable = False
        else:
            zone = "too_far"
            boost = 0.5
            actionable = False
        
        return ProximityMetrics(
            distance=distance,
            proximity_zone=zone,
            boost_factor=boost,
            is_actionable=actionable
        )
    
    def apply_proximity_boost(
        self,
        score: float,
        current_price: float,
        entry_price: float
    ) -> float:
        """Apply proximity boost to score."""
        proximity = self.calculate_proximity(current_price, entry_price)
        
        return score * proximity.boost_factor
    
    def should_wait(
        self,
        current_price: float,
        entry_price: float,
        max_wait_seconds: float = 300
    ) -> bool:
        """Should we wait for better entry?"""
        proximity = self.calculate_proximity(current_price, entry_price)
        
        if proximity.proximity_zone == "hot":
            return False
        
        # Check if we should wait based on volatility
        return proximity.distance > self.hot_zone
    
    def get_entry_adjustment(
        self,
        signal,
        current_price: float
    ) -> Dict[str, any]:
        """Get entry price adjustments."""
        entry_price = getattr(signal, 'entry', None)
        
        if not entry_price:
            return {"action": "none"}
        
        proximity = self.calculate_proximity(current_price, entry_price)
        
        return {
            "proximity": proximity.proximity_zone,
            "distance": proximity.distance,
            "boost": proximity.boost_factor,
            "actionable": proximity.is_actionable,
            "adjust_entry": proximity.is_actionable,
        }


# Price Proximity Model End