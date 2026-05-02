"""
Trading Intelligence Engine - Main Runner.

This is the main entry point for the trading intelligence engine.
It connects all components together.

CRITICAL: This is ANALYSIS ONLY. No auto-trading.
"""

import asyncio
import os
from datetime import datetime
from typing import Dict, List, Optional

from core.signal_engine import (
    SignalEvaluation, FeatureBreakdown, Direction, SetupGrade
)
from core import scoring, confidence, probability as prob_engine
from core import ev, regime
from core import shadow, shadow_live, gate, entry
from backtest import engine as backtest_engine
from backtest import validation
from analytics.journaling import TradeJournal
from config import settings, feature_flags as ff


class TradingEngine:
    """Main trading intelligence engine.
    
    Coordinates all components:
    - Signal evaluation
    - Shadow scoring
    - Backtest validation
    - Live validation
    - Controlled gating
    - Entry logic
    """
    
    def __init__(self):
        # Core components
        self.scoring_engine = scoring.ScoringEngine()
        self.confidence_engine = confidence.ConfidenceEngine(self.scoring_engine)
        self.prob_engine = prob_engine.ProbabilityEngine()
        self.ev_engine = ev.ExpectedValueEngine()
        self.regime_engine = regime.RegimeEngine()
        
        # Validation components
        self.shadow_engine = shadow.ShadowScoringEngine()
        self.backtest_engine = backtest_engine.BacktestEngine()
        self.backtest_validator = validation.BacktestValidationEngine()
        self.live_validator: Optional[shadow_live.ShadowLiveValidationEngine] = None
        
        # Control components
        self.gate = gate.ControlledGate()
        self.entry_engine = entry.EntryEngine()
        
        # Analytics
        self.journal = TradeJournal()
        
        # State
        self.is_running = False
    
    def create_signal(
        self,
        symbol: str,
        direction: str,
        entry: float,
        sl: float,
        tp_levels: List[float],
        features: Dict[str, bool] = None
    ) -> SignalEvaluation:
        """Create and evaluate a signal.
        
        Args:
            symbol: Trading symbol (e.g., "EURUSD")
            direction: "long" or "short"
            entry: Entry price
            sl: Stop loss price
            tp_levels: List of take profit levels
            features: Dict of feature presence
            
        Returns:
            SignalEvaluation with full evaluation
        """
        signal = SignalEvaluation(
            symbol=symbol,
            direction=Direction.LONG if direction == "long" else Direction.SHORT,
            entry=entry,
            sl=sl,
            tp_levels=tp_levels,
        )
        
        # Add features (simplified - in production would detect from data)
        if features:
            for name, present in features.items():
                if present:
                    signal.add_feature(name, FeatureBreakdown(
                        present=True,
                        strength=0.7,
                        age=1,
                        reliability=0.8,
                    ))
        
        # Calculate confidence
        self.confidence_engine.calculate_confidence(signal)
        
        # Calculate probability
        self.prob_engine.calculate_probabilities(signal)
        
        # Calculate EV
        if signal.rr > 0:
            self.ev_engine.calculate_ev(signal)
        
        # Calculate regime
        signal.regime = regime.RegimeType.TREND_UP  # Simplified
        
        # Set grade
        if signal.confidence >= 0.7 and signal.expected_value > 0:
            signal.setup_grade = SetupGrade.A
        elif signal.confidence >= 0.5:
            signal.setup_grade = SetupGrade.B
        else:
            signal.setup_grade = SetupGrade.C
        
        # Calculate RR
        risk = abs(entry - sl)
        if tp_levels and risk > 0:
            signal.rr = (tp_levels[0] - entry) / risk
        
        signal.is_accepted = True
        
        return signal
    
    def evaluate_with_shadow(
        self,
        signal: SignalEvaluation
    ) -> Dict:
        """Evaluate signal with shadow scoring.
        
        Returns main signal + shadow evaluation.
        """
        # Main evaluation (already done)
        
        # Shadow evaluation
        shadow_result = self.shadow_engine.evaluate_signal(signal)
        
        return {
            "main": signal,
            "shadow": shadow_result,
        }
    
    def run_backtest(
        self,
        signals: List[SignalEvaluation]
    ) -> validation.BacktestValidationResult:
        """Run backtest validation."""
        return self.backtest_validator.validate_signals(signals)
    
    def enable_feature(
        self,
        feature_name: str,
        backtest_result: validation.BacktestValidationResult,
        live_result: Optional[Dict] = None
    ) -> bool:
        """Enable feature through controlled gate."""
        # Evaluate backtest
        bt_dict = backtest_result.to_dict()
        self.gate.evaluate_backtest(feature_name, bt_dict)
        
        # Evaluate live if available
        if live_result:
            self.gate.evaluate_live(feature_name, live_result)
        
        # Try to enable
        return self.gate.enable_feature(feature_name)
    
    def calculate_entry(
        self,
        signal: SignalEvaluation
    ) -> entry.EntryResult:
        """Calculate entry for signal."""
        return self.entry_engine.calculate_entry(signal)
    
    def get_status(self) -> Dict:
        """Get engine status."""
        return {
            "is_running": self.is_running,
            "signals_generated": len(self.journal.signals),
            "gate_status": self.gate.get_system_status(),
            "feature_flags": {
                "fvg": ff.ENABLE_FVG,
                "ob": ff.ENABLE_OB,
                "regime": ff.ENABLE_REGIME,
                "probability": ff.ENABLE_PROBABILITY,
                "ev": ff.ENABLE_EV,
            },
        }


def demo_signal_creation():
    """Demo: Create several signals."""
    print("=" * 50)
    print("DEMO: Creating Signals")
    print("=" * 50)
    
    engine = TradingEngine()
    
    # Signal 1: Strong setup
    sig1 = engine.create_signal(
        symbol="EURUSD",
        direction="long",
        entry=1.0850,
        sl=1.0820,
        tp_levels=[1.0900, 1.0920],
        features={"fvg": True, "structure": True, "mitigation": True}
    )
    
    print(f"\nSignal 1: {sig1.symbol} {sig1.direction.value}")
    print(f"  Entry: {sig1.entry}, SL: {sig1.sl}, TP: {sig1.tp_levels}")
    print(f"  Confidence: {sig1.confidence:.0%}")
    print(f"  Grade: {sig1.setup_grade.value}")
    print(f"  EV: {sig1.expected_value:.3f}")
    print(f"  R:R: {sig1.rr:.1f}")
    
    # Signal 2: Weak setup
    sig2 = engine.create_signal(
        symbol="GBPUSD",
        direction="short",
        entry=1.2650,
        sl=1.2680,
        tp_levels=[1.2580],
        features={"mitigation": True}  # Only one feature
    )
    
    print(f"\nSignal 2: {sig2.symbol} {sig2.direction.value}")
    print(f"  Confidence: {sig2.confidence:.0%}")
    print(f"  Grade: {sig2.setup_grade.value}")
    
    # Test shadow evaluation
    print("\n" + "=" * 50)
    print("DEMO: Shadow Evaluation")
    print("=" * 50)
    
    result = engine.evaluate_with_shadow(sig1)
    print(f"Main confidence: {result['main'].confidence:.0%}")
    print(f"Shadow confidence: {result['shadow'].confidence:.0%}")
    print(f"Confidence delta: {result['shadow'].confidence_delta:.3f}")
    
    # Test entry logic
    print("\n" + "=" * 50)
    print("DEMO: Entry Logic")
    print("=" * 50)
    
    entry_result = engine.calculate_entry(sig1)
    print(f"Entry type: {entry_result.entry_type.value}")
    print(f"Entry price: {entry_result.entry_price}")
    print(f"Reason: {entry_result.selection_reason}")
    
    # Engine status
    status = engine.get_status()
    print("\n" + "=" * 50)
    print("ENGINE STATUS")
    print("=" * 50)
    print(f"Total signals: {status['signals_generated']}")
    print(f"Features enabled: {status['gate_status']['enabled']}")
    
    print("\n✅ Trading Engine Demo Complete")


def main():
    """Main entry point."""
    print("""
╔══════════════════════════════════════════════════╗
║                                          ║
║   TRADING INTELLIGENCE ENGINE                ║
║   Professional SMC Analysis System         ║
║                                          ║
║   Type 'demo' to run demo                ║
║   Type 'run' to start bot              ║
║   Type 'quit' to exit                 ║
║                                          ║
╚══════════════════════════════════════════════════╝
    """)
    
    while True:
        cmd = input("\n> ").strip().lower()
        
        if cmd == "demo":
            demo_signal_creation()
        elif cmd == "run":
            print("""
Untuk run bot, perlu:
1. Bot token dari @BotFather
2. Chat ID dari @userinfobot

Contoh penggunaan:
```python
from telegram.bot import TradingBot
import asyncio

async def main():
    bot = TradingBot("YOUR_TOKEN", "YOUR_CHAT_ID")
    await bot.start()

asyncio.run(main())
```
            """)
        elif cmd == "quit":
            print("Sampai jumpa! 👋")
            break
        else:
            print("Perintah tidak dikenal. Coba 'demo', 'run', atau 'quit'.")


if __name__ == "__main__":
    main()