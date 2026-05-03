"""
Integrated Pipeline - Feature Integration.

Manages the pipeline from feature extraction → shadow → validation → enable
with proper feature flags and staged rollout.

CRITICAL: Analysis only - no auto-trading.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from config import feature_flags as ff

# Import new Priority modules
from analytics.normalizer import FeatureNormalizer
from smc.displacement import DisplacementEngine
from smc.liquidity_path import LiquidityPathEngine
from analytics.probability_calibration import ProbabilityCalibrator
from core.opportunity_filter import OpportunityFilter
from core.signal_decay import SignalDecay
from analytics.feature_interactions import FeatureInteractions
from core.regime_weights import RegimeAdaptiveWeights
from core.meta_control import MetaControl
from backtest.shadow_validation import ShadowValidationEngine


@dataclass
class PipelineConfig:
    """Pipeline configuration."""
    
    enable_feature_normalization = ff.ENABLE_FEATURE_NORMALIZATION
    enable_displacement = ff.ENABLE_DISPLACEMENT
    enable_liquidity_path = ff.ENABLE_LIQUIDITY_PATH
    enable_probability_calibration = ff.ENABLE_PROBABILITY_CALIBRATION
    enable_opportunity_filter = ff.ENABLE_OPPORTUNITY_FILTER
    enable_signal_decay = ff.ENABLE_SIGNAL_DECAY
    enable_feature_interactions = ff.ENABLE_FEATURE_INTERACTIONS
    enable_regime_weights = ff.ENABLE_META_ADAPTATION
    enable_meta_control = ff.ENABLE_META_ADAPTATION
    enable_shadow_validation = True


class IntegratedPipeline:
    """Integrated pipeline with all new features."""
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        
        # Priority 1 modules
        self.normalizer = FeatureNormalizer() if config.enable_feature_normalization else None
        self.displacement = DisplacementEngine() if config.enable_displacement else None
        self.liquidity_path = LiquidityPathEngine() if config.enable_liquidity_path else None
        self.prob_calibrator = ProbabilityCalibrator() if config.enable_probability_calibration else None
        
        # Priority 2 modules
        self.opportunity_filter = OpportunityFilter() if config.enable_opportunity_filter else None
        self.signal_decay = SignalDecay() if config.enable_signal_decay else None
        self.feature_interactions = FeatureInteractions() if config.enable_feature_interactions else None
        
        # Priority 3 modules
        self.regime_weights = RegimeAdaptiveWeights() if config.enable_regime_weights else None
        self.meta_control = MetaControl() if config.enable_meta_control else None
        
        # Shadow validation
        self.shadow_validation = ShadowValidationEngine() if config.enable_shadow_validation else None
        
        # Pipeline state
        self.feature_states: Dict[str, str] = {}
        self.trade_history: List[Dict] = []
        
        self._initialize_states()
    
    def _initialize_states(self) -> None:
        """Initialize feature states."""
        all_features = [
            "feature_normalization",
            "displacement",
            "liquidity_path",
            "probability_calibration",
            "opportunity_filter",
            "signal_decay",
            "feature_interactions",
            "regime_weights",
            "meta_control",
        ]
        
        for feature in all_features:
            self.feature_states[feature] = "extraction"
    
    def process_signal(
        self,
        signal_data: Dict[str, Any],
        regime: str = "trend"
    ) -> Dict[str, Any]:
        """Process signal through pipeline."""
        enhanced = signal_data.copy()
        
        # Stage 1: Feature Extraction
        enhanced = self._extract_features(enhanced)
        
        # Stage 2: Enhancement
        enhanced = self._enhance_features(enhanced)
        
        # Stage 3: Shadow scoring
        enhanced = self._shadow_score(enhanced, regime)
        
        # Stage 4: Meta adaptation
        enhanced = self._apply_meta(enhanced, regime)
        
        return enhanced
    
    def _extract_features(self, signal_data: Dict) -> Dict:
        """Extract and normalize features."""
        features = signal_data.get("features", {})
        
        if self.normalizer:
            for name, feature in features.items():
                if isinstance(feature, dict):
                    raw = feature.get("strength", 0)
                    normalized = self.normalizer.normalize(name, raw)
                    feature["normalized_value"] = normalized.normalized_value
                    feature["percentile"] = normalized.percentile
        
        if self.displacement:
            highs = signal_data.get("highs", [])
            lows = signal_data.get("lows", [])
            closes = signal_data.get("closes", [])
            price = signal_data.get("current_price", 0)
            direction = signal_data.get("direction", "bullish")
            
            if highs and lows and closes and price:
                disp = self.displacement.calculate_displacement(
                    highs, lows, closes, price, direction
                )
                signal_data["features"]["displacement"] = {
                    "present": disp.displacement > 0.5,
                    "strength": self.displacement.normalize_displacement(disp),
                    "context": disp.context,
                    "reliability": disp.reliability,
                }
        
        if self.liquidity_path:
            highs = signal_data.get("highs", [])
            lows = signal_data.get("lows", [])
            closes = signal_data.get("closes", [])
            price = signal_data.get("current_price", 0)
            direction = signal_data.get("direction", "long")
            
            if highs and lows and closes and price:
                targets = self.liquidity_path.find_targets(highs, lows, closes, price, direction)
                if targets:
                    best_path = self.liquidity_path.get_best_path(targets, highs, lows, closes, price)
                    if best_path:
                        signal_data["liquidity_path"] = best_path.to_dict()
        
        return signal_data
    
    def _enhance_features(self, signal_data: Dict) -> Dict:
        """Enhance with probability calibration."""
        if self.prob_calibrator:
            score = signal_data.get("confidence", 0.5)
            raw_prob = signal_data.get("probability", 0.5)
            
            calibrated = self.prob_calibrator.calibrate_probability(score, raw_prob)
            
            signal_data["calibrated_probability"] = calibrated.calibrated_probability
            signal_data["probability_confidence"] = calibrated.confidence
        
        return signal_data
    
    def _shadow_score(self, signal_data: Dict, regime: str) -> Dict:
        """Shadow scoring layer."""
        if self.feature_interactions:
            features = signal_data.get("features", {})
            results = self.feature_interactions.get_interaction_stats(features)
            
            if results:
                signal_data["feature_interactions"] = [r.to_dict() for r in results[:5]]
        
        return signal_data
    
    def _apply_meta(self, signal_data: Dict, regime: str) -> Dict:
        """Apply meta-layer adaptations."""
        if self.regime_weights:
            weights = self.regime_weights.get_all_adjusted_weights(regime)
            signal_data["regime_weights"] = weights
        
        if self.meta_control:
            base_confidence = signal_data.get("confidence", 0.5)
            adjusted = self.meta_control.get_confidence_adjustment(base_confidence)
            signal_data["meta_confidence"] = adjusted
            signal_data["meta_adjustments"] = self.meta_control.current_adjustments.copy()
        
        return signal_data
    
    def record_outcome(
        self,
        signal_data: Dict,
        result: str,
        regime: str = "trend"
    ) -> None:
        """Record trade outcome."""
        self.trade_history.append({
            **signal_data,
            "result": result,
            "regime": regime,
            "timestamp": datetime.now(),
        })
        
        if self.normalizer:
            self.normalizer.update_from_outcome(signal_data.get("features", {}), result)
        
        if self.prob_calibrator:
            self.prob_calibrator.record_outcome(signal_data.get("confidence", 0.5), result)
        
        if self.feature_interactions:
            self.feature_interactions.record_outcome(signal_data.get("features", {}), result)
        
        if self.regime_weights:
            self.regime_weights.record_outcome(signal_data.get("features", {}), regime, result)
        
        if self.meta_control:
            self.meta_control.record_trade(result, signal_data.get("confidence", 0.5))
        
        if self.shadow_validation and len(self.trade_history) >= 10:
            self.shadow_validation.load_historical_data(self.trade_history[-100:])
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get pipeline status."""
        return {
            "features": self.feature_states,
            "trade_count": len(self.trade_history),
            "baseline": self.shadow_validation.baseline_metrics if self.shadow_validation else {},
            "meta_health": self.meta_control.get_system_status() if self.meta_control else {},
        }
    
    def validate_feature(self, feature_name: str) -> Dict:
        """Run shadow validation."""
        if not self.shadow_validation:
            return {"status": "disabled"}
        
        validators = {
            "fvg": self.shadow_validation.validate_fvg_feature,
            "order_block": self.shadow_validation.validate_ob_feature,
        }
        
        if feature_name not in validators:
            return {"status": "unknown"}
        
        result = validators[feature_name]()
        return result.to_dict()


# Integrated Pipeline End