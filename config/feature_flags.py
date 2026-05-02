"""
Feature Flags for Trading Intelligence Engine.

Each new feature must be toggleable.
HARD_VETO controls whether disabled features completely block signals.
"""

# SMC Feature Flags
ENABLE_FVG = True           # Fair Value Gap detection
ENABLE_OB = True           # Order Block detection
ENABLE_SMT = True          # Smart Money Tracker (liquidity pool)
ENABLE_MITIGATION = True   # Mitigation zone detection
ENABLE_STRUCTURE = True   # BOS/CHOCH detection
ENABLE_LIQUIDITY = True    # Liquidity pool detection

# Advanced Scoring
ENABLE_REGIME = True       # Market regime detection
ENABLE_PROBABILITY = True # Win probability estimation
ENABLE_EV = True          # Expected Value calculation
ENABLE_SCENARIOS = True   # Scenario analysis
ENABLE_ADAPTIVE_RR = True  # Adaptive Risk/Reward

# Advanced Features
ENABLE_SIGNAL_DECAY = True      # Signal freshness scoring
ENABLE_OPPORTUNITY_FILTER = True # Opportunity cost filtering
ENABLE_CLUSTERING = True        # Signal clustering
ENABLE_NARRATIVE_CHECK = True    # Narrative consistency

# Meta-Layer
ENABLE_META_ADAPTATION = True    # Self-evaluation and adaptation

# Output Control
EMIT_LOGS = True
VERBOSE_TELEGRAM = True         # Send full signal details
HARD_VETO = False               # If True, disabled features block signals

# Performance Flags
ENABLE_BACKTEST = True         # Backtesting engine
ENABLE_SHADOW_MODE = True      # Shadow scoring without affecting signals

# Scoring Weights (adjustable)
DEFAULT_WEIGHTS = {
    "structure": 1.5,
    "liquidity": 1.2,
    "fvg": 1.0,
    "order_block": 1.3,
    "mitigation": 1.1,
    "regime_fit": 0.8,
    "entry_quality": 1.0,
    "smt": 0.7,
}

# Reliability Thresholds
MIN_CONFIDENCE = 0.3
MIN_PROBABILITY = 0.35
MIN_EV = -0.1

# Feature Flags end