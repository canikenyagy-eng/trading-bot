"""
Confidence Engine - Signal Confidence Calculations.

This module calculates and manages signal confidence levels
using component breakdown and reliability weighting.
"""

from typing import Dict, Optional
from dataclasses import dataclass

from core.signal_engine import (
    SignalEvaluation, ConfidenceComponents, Direction
)
from config import feature_flags as ff
from core import scoring


class ConfidenceEngine:
    """Engine for calculating signal confidence."""
    
    def __init__(self, scoring_engine: Optional[scoring.ScoringEngine] = None):
        self.scoring_engine = scoring_engine or scoring.ScoringEngine()
        self.min_confidence = ff.MIN_CONFIDENCE
    
    def calculate_confidence(
        self,
        signal: SignalEvaluation
    ) -> float:
        """Calculate overall confidence for a signal.
        
        Args:
            signal: SignalEvaluation
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Get confidence components
        components = self.calculate_components(signal)
        
        # Update signal
        signal.confidence_components = components
        signal.confidence = components.overall
        
        return signal.confidence
    
    def calculate_components(
        self,
        signal: SignalEvaluation
    ) -> ConfidenceComponents:
        """Calculate confidence breakdown by component.
        
        Uses scoring engine for detailed breakdown.
        
        Args:
            signal: SignalEvaluation
            
        Returns:
            ConfidenceComponents
        """
        return self.scoring_engine.calculate_confidence_components(signal)
    
    def evaluate_confidence(
        self,
        signal: SignalEvaluation
    ) -> tuple[bool, str]:
        """Evaluate if signal meets confidence threshold.
        
        Args:
            signal: SignalEvaluation
            
        Returns:
            Tuple of (passes, reason if fails)
        """
        confidence = signal.confidence
        
        if confidence < self.min_confidence:
            return False, f"confidence_below_minimum ({confidence:.2f} < {self.min_confidence})"
        
        # Check confidence components
        components = signal.confidence_components
        
        if components.structure < 0.2:
            return False, "structure_confidence_too_low"
        
        if components.entry_quality < 0.1:
            return False, "entry_quality_too_low"
        
        return True, ""
    
    def meets_threshold(
        self,
        signal: SignalEvaluation
    ) -> bool:
        """Check if signal meets minimum confidence threshold.
        
        Args:
            signal: SignalEvaluation
            
        Returns:
            True if passes threshold
        """
        passes, _ = self.evaluate_confidence(signal)
        return passes


# Confidence Engine End