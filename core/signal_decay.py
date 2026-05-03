"""
Signal Decay - Time-Based Score Decay.

Applies exponential decay to signal scores based on time
since signal generation.

CRITICAL: Analysis only - no auto-trading.
"""

from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

from config import feature_flags as ff


@dataclass
class DecayResult:
    """Decay calculation result."""
    
    original_score: float = 0.0
    decayed_score: float = 0.0
    decay_factor: float = 0.0
    time_since_signal: float = 0.0  # In minutes
    half_life: float = 60.0  # In minutes
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_score": self.original_score,
            "decayed_score": self.decayed_score,
            "decay_factor": self.decay_factor,
            "time_since_signal": self.time_since_signal,
            "half_life": self.half_life,
        }


class SignalDecay:
    """Signal time decay engine."""
    
    def __init__(self):
        self.enabled = ff.ENABLE_SIGNAL_DECAY
        
        # Decay parameters (in minutes)
        self.half_life = 60.0  # Score halves every 60 minutes
        self.max_decay = 0.5  # Max decay factor
        
        # Time constants
        self.lambda_decay = 0.693 / self.half_life  # Decay constant
    
    def calculate_decay(
        self,
        score: float,
        signal_time: datetime,
        current_time: Optional[datetime] = None
    ) -> DecayResult:
        """Calculate score decay over time.
        
        Args:
            score: Original score
            signal_time: When signal was generated
            current_time: Current time (default: now)
            
        Returns:
            DecayResult with decayed score
        """
        if not self.enabled:
            return DecayResult(
                original_score=score,
                decayed_score=score,
                half_life=self.half_life
            )
        
        if current_time is None:
            current_time = datetime.now()
        
        # Calculate time difference
        time_diff = current_time - signal_time
        time_minutes = time_diff.total_seconds() / 60
        
        # Calculate exponential decay
        decay_factor = self._calculate_decay_factor(time_minutes)
        
        # Apply decay
        decayed_score = score * decay_factor
        
        return DecayResult(
            original_score=score,
            decayed_score=decayed_score,
            decay_factor=decay_factor,
            time_since_signal=time_minutes,
            half_life=self.half_life
        )
    
    def _calculate_decay_factor(
        self,
        time_minutes: float
    ) -> float:
        """Calculate exponential decay factor."""
        # Exponential: exp(-lambda * t)
        import math
        decay_factor = math.exp(-self.lambda_decay * time_minutes)
        
        # Apply max decay cap
        decay_factor = max(decay_factor, self.max_decay)
        
        return decay_factor
    
    def apply_decay_to_signal(
        self,
        signal,
        current_time: Optional[datetime] = None
    ) -> float:
        """Apply decay to signal confidence.
        
        Args:
            signal: SignalEvaluation object
            current_time: Current time
            
        Returns:
            Decayed confidence score
        """
        if not self.enabled:
            return signal.confidence
        
        # Get signal time
        signal_time = getattr(signal, 'generated_at', None)
        if signal_time is None:
            return signal.confidence
        
        # Calculate decay
        result = self.calculate_decay(
            signal.confidence,
            signal_time,
            current_time
        )
        
        return result.decayed_score
    
    def is_expired(
        self,
        signal_time: datetime,
        max_age_minutes: float = 240,
        current_time: Optional[datetime] = None
    ) -> bool:
        """Check if signal is expired.
        
        Args:
            signal_time: When signal was generated
            max_age_minutes: Maximum age before expiration
            current_time: Current time
            
        Returns:
            True if signal is too old
        """
        if current_time is None:
            current_time = datetime.now()
        
        time_diff = current_time - signal_time
        age_minutes = time_diff.total_seconds() / 60
        
        return age_minutes > max_age_minutes
    
    def get_decay_context(
        self,
        signal_time: datetime,
        current_time: Optional[datetime] = None
    ) -> str:
        """Get textual decay context."""
        if current_time is None:
            current_time = datetime.now()
        
        time_diff = current_time - signal_time
        age_minutes = time_diff.total_seconds() / 60
        
        if age_minutes < 15:
            return "fresh"
        elif age_minutes < 60:
            return "recent"
        elif age_minutes < 180:
            return "aging"
        elif age_minutes < 240:
            return "old"
        else:
            return "expired"


# Signal Decay End