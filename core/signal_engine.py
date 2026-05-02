"""
Core Signal Engine - Signal Evaluation Structure.

This module defines the core SignalEvaluation structure used throughout
the trading intelligence engine. Each signal must include comprehensive
metadata for full explainability.

CRITICAL: This is analysis-only. No auto-trading.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
import uuid


class Direction(str, Enum):
    """Trade direction."""
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class SetupGrade(str, Enum):
    """Setup quality grade."""
    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"


class MarketPhase(str, Enum):
    """Market phase classification."""
    ACCUMULATION = "accumulation"
    MANIPULATION = "manipulation"
    DISTRIBUTION = "distribution"
    CONSOLIDATION = "consolidation"
    UNKNOWN = "unknown"


class TimingState(str, Enum):
    """Signal timing state."""
    READY_NOW = "ready_now"
    WAITING = "waiting"
    EARLY = "early"
    EXPIRED = "expired"


class RegimeType(str, Enum):
    """Market regime type."""
    TREND_UP = "trend_up"
    TREND_DOWN = "trend_down"
    RANGE = "range"
    VOLATILE = "volatile"
    LOW_VOLATILITY = "low_volatility"


class SessionType(str, Enum):
    """Trading session type."""
    SYDNEY = "sydney"
    TOKYO = "tokyo"
    LONDON = "london"
    NEW_YORK = "new_york"
    OFF_SESSION = "off_session"


@dataclass
class FeatureBreakdown:
    """Individual feature detection results.
    
    Each feature must include: presence, strength, context, reliability.
    """
    
    # Basic presence
    present: bool = False
    
    # Feature strength (0.0 to 1.0)
    strength: float = 0.0
    
    # Age in bars (how recent)
    age: int = 0
    
    # Filled/mitigated status
    filled: bool = False
    
    # Reliability score (0.0 to 1.0)
    reliability: float = 0.0
    
    # Additional metadata
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "present": self.present,
            "strength": self.strength,
            "age": self.age,
            "filled": self.filled,
            "reliability": self.reliability,
            "details": self.details,
        }


@dataclass
class ScoreComponent:
    """Individual score component contribution."""
    
    feature: str
    raw_score: float = 0.0
    weight: float = 1.0
    reliability: float = 1.0
    
    # Contributing factors
    component_details: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def weighted_score(self) -> float:
        """Calculate weighted score = raw_score × weight × reliability."""
        return self.raw_score * self.weight * self.reliability


@dataclass
class ScenarioAnalysis:
    """Trade scenario analysis."""
    
    # Primary scenario
    primary: Dict[str, Any] = field(default_factory=dict)
    
    # Alternative scenarios
    alternative: Dict[str, Any] = field(default_factory=dict)
    
    # Invalidation condition
    invalidation: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary": self.primary,
            "alternative": self.alternative,
            "invalidation": self.invalidation,
        }


@dataclass
class ConfidenceComponents:
    """Breakdown of confidence by component."""
    
    structure: float = 0.0       # Structure (BOS/CHOCH) confidence
    liquidity: float = 0.0      # Liquidity pool confidence
    entry_quality: float = 0.0   # Entry zone quality
    regime_fit: float = 0.0      # How well setup fits regime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "structure": self.structure,
            "liquidity": self.liquidity,
            "entry_quality": self.entry_quality,
            "regime_fit": self.regime_fit,
        }
    
    @property
    def overall(self) -> float:
        """Calculate overall weighted confidence."""
        weights = {"structure": 0.30, "liquidity": 0.25, "entry_quality": 0.25, "regime_fit": 0.20}
        return (
            self.structure * weights["structure"] +
            self.liquidity * weights["liquidity"] +
            self.entry_quality * weights["entry_quality"] +
            self.regime_fit * weights["regime_fit"]
        )


@dataclass
class Probabilities:
    """Trade outcome probabilities."""
    
    tp_hit: float = 0.5          # Probability of taking profit
    sl_hit: float = 0.5          # Probability of stop loss
    breakeven: float = 0.0       # Probability of breakeven exit
    
    # Confidence in probability estimate
    confidence: float = 0.5
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tp_hit": self.tp_hit,
            "sl_hit": self.sl_hit,
            "breakeven": self.breakeven,
            "confidence": self.confidence,
        }


@dataclass
class RiskPlan:
    """Risk management plan."""
    
    risk_percent: float = 0.02    # Risk as percentage of account
    position_size: float = 0.0  # Calculated position size
    current_risk: float = 0.0   # Current risk amount
    
    # Stop loss in pips
    sl_pips: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_percent": self.risk_percent,
            "position_size": self.position_size,
            "current_risk": self.current_risk,
            "sl_pips": self.sl_pips,
        }


@dataclass
class NarrativeSection:
    """Signal narrative for explainability."""
    
    htf_bias: str = ""           # Higher timeframe bias
    structure_state: str = ""    # Current structure state
    liquidity_context: str = "" # Liquidity pool context
    entry_logic: str = ""        # Entry logic explanation
    risk_explanation: str = ""   # Risk explanation
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "htf_bias": self.htf_bias,
            "structure_state": self.structure_state,
            "liquidity_context": self.liquidity_context,
            "entry_logic": self.entry_logic,
            "risk_explanation": self.risk_explanation,
        }


@dataclass
class SignalEvaluation:
    """Comprehensive signal evaluation structure.
    
    This is the core output of the trading intelligence engine.
    Each signal includes full metadata for explainability and analysis.
    
    CRITICAL: Analysis-only. No auto-trading execution.
    """
    
    # Identity
    signal_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Symbol & Direction
    symbol: str = ""
    direction: Direction = Direction.FLAT
    
    # Entry Levels
    entry: float = 0.0
    sl: float = 0.0
    
    # Take Profit Levels
    tp_levels: List[float] = field(default_factory=list)
    tp_zone: tuple = (0.0, 0.0)
    
    # Risk/Reward
    rr: float = 0.0              # Risk/Reward ratio
    
    # Confidence
    confidence: float = 0.0
    confidence_components: ConfidenceComponents = field(default_factory=ConfidenceComponents)
    
    # Probabilities
    probabilities: Probabilities = field(default_factory=Probabilities)
    
    # Expected Value
    expected_value: float = 0.0
    
    # Setup Quality
    setup_grade: SetupGrade = SetupGrade.C
    
    # Timing
    timing: TimingState = TimingState.WAITING
    
    # Market Context
    regime: RegimeType = RegimeType.RANGE
    market_phase: MarketPhase = MarketPhase.UNKNOWN
    
    # Liquidity
    liquidity_path: str = ""
    
    # Feature Breakdown (new - for Step 1)
    features: Dict[str, FeatureBreakdown] = field(default_factory=dict)
    
    # Score Components (new - for Step 1)
    score_components: List[ScoreComponent] = field(default_factory=list)
    
    # Narrative
    narrative: NarrativeSection = field(default_factory=NarrativeSection)
    
    # Scenarios
    scenarios: ScenarioAnalysis = field(default_factory=ScenarioAnalysis)
    
    # Risk Plan
    risk_plan: RiskPlan = field(default_factory=RiskPlan)
    
    # Session Context
    session_context: SessionType = SessionType.OFF_SESSION
    correlation_note: str = ""
    
    # Rejection Reasons (new - for Step 1)
    rejection_reasons: List[str] = field(default_factory=list)
    
    # Additional Details
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Status Flags
    is_valid: bool = True
    is_accepted: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert signal to dictionary for output."""
        return {
            "signal_id": self.signal_id,
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "direction": self.direction.value,
            "entry": self.entry,
            "sl": self.sl,
            "tp_levels": self.tp_levels,
            "tp_zone": list(self.tp_zone) if self.tp_zone else [],
            "rr": self.rr,
            "confidence": self.confidence,
            "confidence_components": self.confidence_components.to_dict(),
            "probabilities": self.probabilities.to_dict(),
            "expected_value": self.expected_value,
            "setup_grade": self.setup_grade.value,
            "timing": self.timing.value,
            "regime": self.regime.value,
            "market_phase": self.market_phase.value,
            "liquidity_path": self.liquidity_path,
            "features": {k: v.to_dict() for k, v in self.features.items()},
            "score_components": [s.__dict__ for s in self.score_components],
            "narrative": self.narrative.to_dict(),
            "scenarios": self.scenarios.to_dict(),
            "risk_plan": self.risk_plan.to_dict(),
            "session_context": self.session_context.value,
            "correlation_note": self.correlation_note,
            "rejection_reasons": self.rejection_reasons,
            "details": self.details,
            "is_valid": self.is_valid,
            "is_accepted": self.is_accepted,
        }
    
    @property
    def total_score(self) -> float:
        """Calculate total weighted score from components."""
        return sum(c.weighted_score for c in self.score_components)
    
    @property
    def is_rejected(self) -> bool:
        """Check if signal was rejected."""
        return len(self.rejection_reasons) > 0 or not self.is_valid
    
    def add_rejection_reason(self, reason: str) -> None:
        """Add a rejection reason."""
        if reason not in self.rejection_reasons:
            self.rejection_reasons.append(reason)
            self.is_valid = False
    
    def add_feature(self, name: str, feature: FeatureBreakdown) -> None:
        """Add a feature detection result."""
        self.features[name] = feature
    
    def add_score_component(self, component: ScoreComponent) -> None:
        """Add a score component."""
        self.score_components.append(component)


@dataclass
class SignalSet:
    """Collection of signals for portfolio management."""
    
    signals: List[SignalEvaluation] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def add(self, signal: SignalEvaluation) -> None:
        """Add a signal to the set."""
        self.signals.append(signal)
    
    def get_accepted(self) -> List[SignalEvaluation]:
        """Get all accepted signals."""
        return [s for s in self.signals if s.is_accepted]
    
    def get_by_direction(self, direction: Direction) -> List[SignalEvaluation]:
        """Get signals by direction."""
        return [s for s in self.signals if s.direction == direction]
    
    def get_by_symbol(self, symbol: str) -> List[SignalEvaluation]:
        """Get signals by symbol."""
        return [s for s in self.signals if s.symbol == symbol]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "count": len(self.signals),
            "signals": [s.to_dict() for s in self.signals],
        }


# Signal Engine End