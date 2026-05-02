"""
Controlled Gate - Feature Enable/Disable Based on Validation.

This module implements the controlled enable system that gates
features based on backtest and live validation results.

CRITICAL: This controls feature flags, NOT actual trade execution.
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from config import feature_flags as ff


class ValidationStage(str, Enum):
    """Validation stages (ordered by progression)."""
    DISABLED = "disabled"       # Feature not being tested
    SHADOW = "shadow"         # Shadow scoring only
    BACKTEST = "backtest"     # Backtest validation
    SHADOW_LIVE = "shadow_live"  # Live monitoring
    ENABLED = "enabled"       # Fully enabled (controlled)
    
    def can_transition_to(self, next_stage: 'ValidationStage') -> bool:
        """Check if transition is valid."""
        valid_transitions = {
            ValidationStage.DISABLED: {ValidationStage.SHADOW},
            ValidationStage.SHADOW: {ValidationStage.BACKTEST, ValidationStage.DISABLED},
            ValidationStage.BACKTEST: {ValidationStage.SHADOW_LIVE, ValidationStage.SHADOW},
            ValidationStage.SHADOW_LIVE: {ValidationStage.ENABLED, ValidationStage.BACKTEST},
            ValidationStage.ENABLED: {ValidationStage.SHADOW_LIVE},  # Can be disabled
        }
        return next_stage in valid_transitions.get(self, set())


@dataclass
class FeatureGate:
    """Individual feature gate."""
    
    feature_name: str
    
    # Current state
    stage: ValidationStage = ValidationStage.DISABLED
    
    # Validation results
    backtest_valid: bool = False
    live_valid: bool = False
    stability_score: float = 0.0
    
    # Control
    is_enabled: bool = False  # Whether feature is actively used
    
    # History
    stage_history: List[Dict] = field(default_factory=list)
    
    # Timestamps
    enabled_at: Optional[datetime] = None
    disabled_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_name": self.feature_name,
            "stage": self.stage.value,
            "backtest_valid": self.backtest_valid,
            "live_valid": self.live_valid,
            "stability_score": self.stability_score,
            "is_enabled": self.is_enabled,
            "enabled_at": self.enabled_at.isoformat() if self.enabled_at else None,
        }


class ControlledGate:
    """Controlled gate system for features.
    
    This manages feature enable/disable based on validation.
    
    CRITICAL: This controls feature flags, NOT trades.
    """
    
    def __init__(self):
        # Feature gates
        self.gates: Dict[str, FeatureGate] = {}
        
        # Parameters
        self.min_backtest_trades = 20
        self.min_live_trades = 10
        self.min_stability = 0.5
        self.min_winrate = 0.40
        
        # Stage transition callbacks
        self._on_stage_change: List[callable] = []
        
        # Initialize default gates
        self._initialize_default_gates()
    
    def _initialize_default_gates(self) -> None:
        """Initialize gates for all features."""
        # Get all feature flags that are toggleable
        feature_names = [
            "fvg", "order_block", "structure", "liquidity",
            "mitigation", "smt", "regime", "probability",
            "ev", "scenarios", "adaptive_rr"
        ]
        
        for name in feature_names:
            self.gates[name] = FeatureGate(feature_name=name)
    
    def register_callback(self, callback: callable) -> None:
        """Register stage change callback."""
        self._on_stage_change.append(callback)
    
    def evaluate_backtest(
        self,
        feature_name: str,
        backtest_result: Dict[str, Any]
    ) -> FeatureGate:
        """Evaluate backtest result for feature.
        
        Args:
            feature_name: Name of feature
            backtest_result: Backtest validation result
            
        Returns:
            Updated FeatureGate
        """
        gate = self._get_or_create_gate(feature_name)
        
        # Check if backtest valid
        winrate = backtest_result.get("winrate", 0.0)
        stability = backtest_result.get("stability_score", 0.0)
        trades = backtest_result.get("total_trades", 0)
        
        backtest_valid = (
            trades >= self.min_backtest_trades and
            winrate >= self.min_winrate and
            stability >= self.min_stability
        )
        
        gate.stability_score = stability
        gate.backtest_valid = backtest_valid
        
        # Transition stage if valid
        if backtest_valid and gate.stage == ValidationStage.SHADOW:
            gate.stage = ValidationStage.BACKTEST
            self._record_stage_change(gate, f"backtest_valid_winrate_{winrate:.0%}")
        
        return gate
    
    def evaluate_live(
        self,
        feature_name: str,
        live_result: Dict[str, Any]
    ) -> FeatureGate:
        """Evaluate live validation for feature.
        
        Args:
            feature_name: Name of feature
            live_result: Live validation result
            
        Returns:
            Updated FeatureGate
        """
        gate = self._get_or_create_gate(feature_name)
        
        # Check if live valid
        convergence = live_result.get("convergence_score", 0.0)
        live_valid = live_result.get("confidence_valid", False)
        trades = live_result.get("live_outcomes", 0)
        
        live_valid = live_valid and trades >= self.min_live_trades
        
        gate.live_valid = live_valid
        
        # Adjust stability based on drift
        if live_result.get("drift_detected"):
            if live_result.get("drift_type") == "negative":
                gate.stability_score *= 0.8  # Reduce stability
        
        # Transition stage if valid
        if live_valid and gate.stage == ValidationStage.BACKTEST:
            gate.stage = ValidationStage.SHADOW_LIVE
            self._record_stage_change(gate, f"live_valid_convergence_{convergence:.0%}")
        
        return gate
    
    def enable_feature(
        self,
        feature_name: str
    ) -> bool:
        """Enable feature if conditions met.
        
        Args:
            feature_name: Name of feature
            
        Returns:
            True if enabled, False if not ready
        """
        gate = self._get_or_create_gate(feature_name)
        
        # Check ready for enable
        ready = (
            gate.backtest_valid and
            gate.live_valid and
            gate.stability_score >= self.min_stability
        )
        
        if not ready:
            return False
        
        # Check stage transition
        if not gate.stage.can_transition_to(ValidationStage.ENABLED):
            return False
        
        # Enable
        gate.stage = ValidationStage.ENABLED
        gate.is_enabled = True
        gate.enabled_at = datetime.now()
        
        self._record_stage_change(gate, "enabled")
        
        # Update feature flag
        self._update_feature_flag(feature_name, True)
        
        # Notify callbacks
        self._notify_stage_change(gate)
        
        return True
    
    def disable_feature(
        self,
        feature_name: str,
        reason: str = ""
    ) -> bool:
        """Disable feature.
        
        Args:
            feature_name: Name of feature
            reason: Reason for disabling
            
        Returns:
            True if disabled
        """
        gate = self._get_or_create_gate(feature_name)
        
        gate.stage = ValidationStage.DISABLED
        gate.is_enabled = False
        gate.disabled_at = datetime.now()
        
        self._record_stage_change(gate, f"disabled_{reason}")
        
        # Update feature flag
        self._update_feature_flag(feature_name, False)
        
        # Notify callbacks
        self._notify_stage_change(gate)
        
        return True
    
    def _get_or_create_gate(
        self,
        feature_name: str
    ) -> FeatureGate:
        """Get or create gate for feature."""
        if feature_name not in self.gates:
            self.gates[feature_name] = FeatureGate(feature_name=feature_name)
        
        return self.gates[feature_name]
    
    def _record_stage_change(
        self,
        gate: FeatureGate,
        cause: str
    ) -> None:
        """Record stage change in history."""
        gate.stage_history.append({
            "stage": gate.stage.value,
            "cause": cause,
            "timestamp": datetime.now().isoformat(),
        })
    
    def _update_feature_flag(
        self,
        feature_name: str,
        enabled: bool
    ) -> None:
        """Update feature flag in config."""
        flag_map = {
            "fvg": "ENABLE_FVG",
            "order_block": "ENABLE_OB",
            "structure": "ENABLE_STRUCTURE",
            "liquidity": "ENABLE_LIQUIDITY",
            "mitigation": "ENABLE_MITIGATION",
            "smt": "ENABLE_SMT",
            "regime": "ENABLE_REGIME",
            "probability": "ENABLE_PROBABILITY",
            "ev": "ENABLE_EV",
            "scenarios": "ENABLE_SCENARIOS",
            "adaptive_rr": "ENABLE_ADAPTIVE_RR",
        }
        
        flag = flag_map.get(feature_name)
        if flag and hasattr(ff, flag):
            setattr(ff, flag, enabled)
    
    def _notify_stage_change(self, gate: FeatureGate) -> None:
        """Notify callbacks of stage change."""
        for callback in self._on_stage_change:
            try:
                callback(gate)
            except:
                pass  # Ignore callback errors
    
    def get_enabled_features(self) -> List[str]:
        """Get list of enabled features."""
        return [
            name for name, gate in self.gates.items()
            if gate.is_enabled
        ]
    
    def get_disabled_features(self) -> List[str]:
        """Get list of disabled features."""
        return [
            name for name, gate in self.gates.items()
            if not gate.is_enabled and gate.stage == ValidationStage.DISABLED
        ]
    
    def get_features_by_stage(
        self,
        stage: ValidationStage
    ) -> List[str]:
        """Get features in specific stage."""
        return [
            name for name, gate in self.gates.items()
            if gate.stage == stage
        ]
    
    def get_gate_status(
        self,
        feature_name: str
    ) -> Dict[str, Any]:
        """Get gate status for feature."""
        gate = self._get_or_create_gate(feature_name)
        
        return {
            "feature": feature_name,
            "stage": gate.stage.value,
            "is_enabled": gate.is_enabled,
            "backtest_valid": gate.backtest_valid,
            "live_valid": gate.live_valid,
            "stability": gate.stability_score,
            "stage_history": gate.stage_history[-3:],
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        stages = {}
        
        for stage in ValidationStage:
            stages[stage.value] = len(self.get_features_by_stage(stage))
        
        return {
            "total_features": len(self.gates),
            "enabled": len(self.get_enabled_features()),
            "by_stage": stages,
        }
    
    def force_stage(
        self,
        feature_name: str,
        stage: ValidationStage
    ) -> None:
        """Force feature to specific stage (for testing)."""
        gate = self._get_or_create_gate(feature_name)
        old_stage = gate.stage
        
        gate.stage = stage
        
        if stage == ValidationStage.ENABLED:
            gate.is_enabled = True
            gate.enabled_at = datetime.now()
            self._update_feature_flag(feature_name, True)
        elif old_stage == ValidationStage.ENABLED:
            gate.is_enabled = False
            gate.disabled_at = datetime.now()
            self._update_feature_flag(feature_name, False)
        
        self._record_stage_change(gate, f"forced_{stage.value}")


# Controlled Gate End