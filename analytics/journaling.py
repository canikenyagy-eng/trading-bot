"""
Analytics Journaling Module - Trade Logging.

This module logs all signals and outcomes for analysis.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json

from core.signal_engine import SignalEvaluation, Direction


@dataclass
class TradeJournal:
    """Trade journal for recording signals and outcomes."""
    
    signals: List[SignalEvaluation] = field(default_factory=list)
    outcomes: List[Dict] = field(default_factory=list)
    
    # Statistics
    total_signals: int = 0
    accepted_signals: int = 0
    rejected_signals: int = 0
    
    def add_signal(self, signal: SignalEvaluation) -> None:
        """Add signal to journal."""
        self.signals.append(signal)
        self.total_signals += 1
        
        if signal.is_accepted:
            self.accepted_signals += 1
        else:
            self.rejected_signals += 1
    
    def record_outcome(
        self,
        signal_id: str,
        symbol: str,
        direction: str,
        entry: float,
        exit: float,
        result: str,  # "tp", "sl", "be"
        rr_achieved: float
    ) -> None:
        """Record trade outcome."""
        outcome = {
            "signal_id": signal_id,
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "direction": direction,
            "entry": entry,
            "exit": exit,
            "result": result,
            "rr_achieved": rr_achieved,
        }
        
        self.outcomes.append(outcome)
    
    def get_outcomes_by_feature(
        self,
        feature_name: str
    ) -> List[Dict]:
        """Get outcomes filtered by feature presence."""
        outputs = []
        
        for signal in self.signals:
            if feature_name in signal.features:
                if signal.features[feature_name].present:
                    # Find matching outcome
                    for outcome in self.outcomes:
                        if outcome["signal_id"] == signal.signal_id:
                            outputs.append(outcome)
        
        return outputs
    
    def get_winrate_by_feature(
        self,
        feature_name: str,
        min_samples: int = 5
    ) -> float:
        """Calculate win rate for a feature."""
        outcomes = self.get_outcomes_by_feature(feature_name)
        
        if len(outcomes) < min_samples:
            return 0.5
        
        wins = sum(1 for o in outcomes if o["result"] == "tp")
        return wins / len(outcomes)
    
    def get_symbol_stats(
        self,
        symbol: str
    ) -> Dict[str, Any]:
        """Get statistics for a symbol."""
        symbol_outcomes = [o for o in self.outcomes if o["symbol"] == symbol]
        
        if not symbol_outcomes:
            return {
                "total_trades": 0,
                "win_rate": 0.5,
                "avg_rr": 0.0,
            }
        
        wins = sum(1 for o in symbol_outcomes if o["result"] == "tp")
        total = len(symbol_outcomes)
        avg_rr = sum(o["rr_achieved"] for o in symbol_outcomes) / total
        
        return {
            "total_trades": total,
            "win_rate": wins / total,
            "avg_rr": avg_rr,
        }
    
    def get_recent_performance(
        self,
        n: int = 50
    ) -> Dict[str, Any]:
        """Get performance from recent trades."""
        recent = self.outcomes[-n:] if self.outcomes else []
        
        if not recent:
            return {
                "win_rate": 0.5,
                "avg_rr": 0.0,
                "profit_factor": 0.0,
            }
        
        wins = sum(1 for o in recent if o["result"] == "tp")
        total = len(recent)
        
        r_total = sum(o["rr_achieved"] for o in recent)
        r_losses = sum(
            -1 for o in recent 
            if o["result"] == "sl" and o["rr_achieved"] < 0
        )
        
        profit_factor = abs(r_total / r_losses) if r_losses > 0 else float('inf')
        
        return {
            "win_rate": wins / total,
            "avg_rr": r_total / total,
            "profit_factor": profit_factor,
            "total_trades": total,
        }
    
    def export_json(self, filepath: str) -> None:
        """Export journal to JSON."""
        data = {
            "signals": [s.to_dict() for s in self.signals],
            "outcomes": self.outcomes,
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def import_json(self, filepath: str) -> None:
        """Import journal from JSON."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.signals = []
        self.outcomes = data.get("outcomes", [])


# Journaling Module End