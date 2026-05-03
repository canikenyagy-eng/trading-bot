"""
Signal State Machine - Signal Lifecycle Management.

Manages signal states from creation to completion.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class SignalState(Enum):
    """Signal states."""
    EARLY = "early"
    WAITING = "waiting"
    READY = "ready"
    TRIGGERED = "triggered"
    EXPIRED = "expired"
    INVALID = "invalid"
    CANCELLED = "cancelled"


class SignalStateMachine:
    """Signal state machine manager."""
    
    def __init__(self):
        # State thresholds
        self.early_to_ready_seconds = 300  # 5 minutes
        self.ready_timeout_seconds = 1800  # 30 minutes
        self.max_lifetime_seconds = 3600  # 1 hour
        
        # State transitions tracking
        self.transitions: Dict[str, List[datetime]] = {
            "early_to_ready": [],
            "waiting_to_ready": [],
            "ready_to_triggered": [],
            "to_expired": [],
            "to_invalid": [],
        }
    
    def initialize_signal(self, signal) -> SignalState:
        """Initialize a new signal."""
        if not hasattr(signal, 'signal_state'):
            signal.signal_state = SignalState.EARLY
        
        if not hasattr(signal, 'state_created_at'):
            signal.state_created_at = datetime.now()
        
        if not hasattr(signal, 'state_history'):
            signal.state_history = []
        
        return signal.signal_state
    
    def _record_transition(self, signal, state: SignalState) -> None:
        """Record transition in history."""
        if hasattr(signal, 'state_history'):
            signal.state_history.append({
                "to": state.value,
                "timestamp": datetime.now()
            })
    
    def get_state(self, signal) -> SignalState:
        """Get current state."""
        return getattr(signal, 'signal_state', SignalState.EARLY)
    
    def can_transition_to(self, current: SignalState, target: SignalState) -> bool:
        """Check if transition is valid."""
        valid_transitions = {
            SignalState.EARLY: [SignalState.WAITING, SignalState.READY, SignalState.EXPIRED, SignalState.INVALID],
            SignalState.WAITING: [SignalState.READY, SignalState.EXPIRED, SignalState.INVALID],
            SignalState.READY: [SignalState.TRIGGERED, SignalState.EXPIRED, SignalState.CANCELLED],
            SignalState.TRIGGERED: [],
            SignalState.EXPIRED: [],
            SignalState.INVALID: [],
            SignalState.CANCELLED: [],
        }
        
        return target in valid_transitions.get(current, [])
    
    def transition_to(self, signal, target: SignalState) -> bool:
        """Transition signal to new state."""
        current = self.get_state(signal)
        
        if not self.can_transition_to(current, target):
            return False
        
        # Perform transition
        old_state = signal.signal_state
        signal.signal_state = target
        
        # Record in history
        if hasattr(signal, 'state_history'):
            signal.state_history.append({
                "from": old_state.value,
                "to": target.value,
                "timestamp": datetime.now()
            })
        
        # Track transitions
        key = f"{old_state.value}_{target.value}"
        if key in self.transitions:
            self.transitions[key].append(datetime.now())
        
        return True
    
    def update_state(self, signal, current_price: float = None, entry_price: float = None) -> SignalState:
        """Update signal state based on time and price."""
        state = self.get_state(signal)
        created_at = getattr(signal, 'state_created_at', datetime.now())
        age = (datetime.now() - created_at).total_seconds()
        
        # Auto transitions based on time
        if state == SignalState.EARLY and age > self.early_to_ready_seconds:
            self.transition_to(signal, SignalState.WAITING)
            state = SignalState.WAITING
        
        if state == SignalState.WAITING and age > self.ready_timeout_seconds:
            self.transition_to(signal, SignalState.READY)
            state = SignalState.READY
        
        if state in (SignalState.READY, SignalState.WAITING) and age > self.max_lifetime_seconds:
            self.transition_to(signal, SignalState.EXPIRED)
            state = SignalState.EXPIRED
        
        # Price-based transitions
        if current_price and entry_price:
            if state in (SignalState.WAITING, SignalState.EARLY):
                distance = abs(current_price - entry_price) / entry_price
                
                if distance < 0.001:  # Within 0.1%
                    self.transition_to(signal, SignalState.READY)
                    state = SignalState.READY
                elif distance > 0.01:  # More than 1% away
                    # Start timeout
                    if not hasattr(signal, 'price_timeout_started'):
                        signal.price_timeout_started = datetime.now()
                elif hasattr(signal, 'price_timeout_started'):
                    timeout_age = (datetime.now() - signal.price_timeout_started).total_seconds()
                    if timeout_age > 300:  # 5 minutes too far
                        self.transition_to(signal, SignalState.EXPIRED)
        
        return self.get_state(signal)
    
    def is_actionable(self, signal) -> bool:
        """Check if signal is actionable."""
        state = self.get_state(signal)
        return state in (SignalState.READY, SignalState.WAITING)
    
    def cancel_signal(self, signal) -> bool:
        """Cancel signal."""
        return self.transition_to(signal, SignalState.CANCELLED)
    
    def invalidate_signal(self, signal) -> bool:
        """Invalidate signal."""
        return self.transition_to(signal, SignalState.INVALID)
    
    def get_time_in_state(self, signal) -> float:
        """Get seconds in current state."""
        state = self.get_state(signal)
        created_at = getattr(signal, 'state_created_at', datetime.now())
        return (datetime.now() - created_at).total_seconds()
    
    def get_transition_stats(self) -> Dict[str, int]:
        """Get transition statistics."""
        return {
            key: len(vals) for key, vals in self.transitions.items()
        }


# Signal State Machine End