"""
Real-Time Signal Queue - Signal Flow Management.

Manages signal stream in real-time with continuous re-ranking.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import time


@dataclass
class QueuedSignal:
    """Signal in queue."""
    
    signal: Any
    created_at: datetime
    state: str = "pending"  # pending, active, expired
    dynamic_score: float = 0.0
    times_ranked: int = 0
    last_update: datetime = None
    
    @property
    def age_seconds(self) -> float:
        return (datetime.now() - self.created_at).total_seconds()
    
    @property
    def is_expired(self) -> bool:
        return self.state == "expired"


class SignalQueue:
    """Real-time signal queue manager."""
    
    def __init__(self):
        # Queue configuration
        self.max_queue_size = 20
        self.max_lifetime = 3600  # 1 hour in seconds
        self.re_rank_interval = 60  # 1 minute
        
        # Queues
        self.pending: List[QueuedSignal] = []
        self.active: List[QueuedSignal] = []
        self.expired: List[QueuedSignal] = []
        
        # History tracking
        self.total_received = 0
        self.total_expired = 0
        self.total_triggered = 0
    
    def add_signal(self, signal, priority_score: float = 0.5) -> QueuedSignal:
        """Add signal to queue."""
        # Check queue size
        if len(self.pending) >= self.max_queue_size:
            # Remove lowest priority
            self._remove_lowest()
        
        queued = QueuedSignal(
            signal=signal,
            created_at=datetime.now(),
            dynamic_score=priority_score
        )
        
        self.pending.append(queued)
        self.total_received += 1
        
        return queued
    
    def remove_signal(self, signal) -> bool:
        """Remove specific signal."""
        for qs in self.pending:
            if qs.signal is signal:
                self.pending.remove(qs)
                return True
        return False
    
    def _remove_lowest(self) -> None:
        """Remove lowest priority signal."""
        if not self.pending:
            return
        
        lowest = min(self.pending, key=lambda qs: qs.dynamic_score)
        lowest.state = "expired"
        self.expired.append(lowest)
        self.pending.remove(lowest)
        self.total_expired += 1
    
    def update_scores(self, score_func) -> None:
        """Update all scores using function."""
        for qs in self.pending:
            qs.dynamic_score = score_func(qs.signal)
            qs.last_update = datetime.now()
            qs.times_ranked += 1
    
    def re_rank(self) -> List[QueuedSignal]:
        """Re-rank pending signals by score."""
        self.pending.sort(key=lambda qs: qs.dynamic_score, reverse=True)
        
        # Update rank positions
        for i, qs in enumerate(self.pending):
            qs.times_ranked = i
        
        return self.pending
    
    def check_expiration(self, max_lifetime: int = None) -> List[QueuedSignal]:
        """Check and expire old signals."""
        lifetime = max_lifetime or self.max_lifetime
        
        newly_expired = []
        to_remove = []
        
        for qs in self.pending:
            if qs.age_seconds > lifetime:
                qs.state = "expired"
                self.expired.append(qs)
                to_remove.append(qs)
                newly_expired.append(qs)
                self.total_expired += 1
        
        for qs in to_remove:
            self.pending.remove(qs)
        
        return newly_expired
    
    def activate_top(self, count: int = 3) -> List[QueuedSignal]:
        """Move top signals to active."""
        top = []
        
        for _ in range(min(count, len(self.pending))):
            qs = self.pending.pop(0)
            qs.state = "active"
            self.active.append(qs)
            top.append(qs)
            self.total_triggered += 1
        
        return top
    
    def mark_triggered(self, signal) -> bool:
        """Mark signal as triggered (taken)."""
        for qs in self.active:
            if qs.signal is signal:
                qs.state = "triggered"
                self.active.remove(qs)
                return True
        return False
    
    def get_active_count(self) -> int:
        """Get count of active signals."""
        return len(self.active)
    
    def get_pending_count(self) -> int:
        """Get count of pending signals."""
        return len(self.pending)
    
    def clear_expired(self) -> int:
        """Clear expired signals."""
        count = len(self.expired)
        self.expired.clear()
        return count
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            "pending": len(self.pending),
            "active": len(self.active),
            "expired": len(self.expired),
            "total_received": self.total_received,
            "total_expired": self.total_expired,
            "total_triggered": self.total_triggered,
            "trigger_rate": self.total_triggered / self.total_received if self.total_received > 0 else 0,
        }


# Signal Queue End