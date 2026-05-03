"""
Regime Robustness Test - Performance by Market Regime.

Evaluates system performance across different market conditions.
"""

from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class RegimeMetrics:
    """Metrics for a specific regime."""
    
    regime: str
    trade_count: int
    win_rate: float
    profit_factor: float
    avg_r: float
    max_drawdown: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "regime": self.regime,
            "trade_count": self.trade_count,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "avg_r": self.avg_r,
            "max_drawdown": self.max_drawdown,
        }


class RegimeRobustnessTest:
    """Regime robustness validation."""
    
    def __init__(self):
        self.enabled = True
    
    def categorize_by_regime(
        self,
        trades: List[Dict],
        regime_field: str = "regime"
    ) -> Dict[str, List[Dict]]:
        """Categorize trades by regime."""
        by_regime = {}
        
        for trade in trades:
            regime = trade.get(regime_field, "unknown")
            
            if regime not in by_regime:
                by_regime[regime] = []
            
            by_regime[regime].append(trade)
        
        return by_regime
    
    def calculate_regime_metrics(
        self,
        regime_trades: List[Dict]
    ) -> RegimeMetrics:
        """Calculate metrics for regime."""
        if not regime_trades:
            return RegimeMetrics(
                regime="",
                trade_count=0,
                win_rate=0,
                profit_factor=0,
                avg_r=0,
                max_drawdown=0
            )
        
        wins = sum(1 for t in regime_trades if t.get("result") == "tp")
        total = len(regime_trades)
        
        win_rate = wins / total if total > 0 else 0
        
        # R values
        rr = [t.get("rr", 0) for t in regime_trades]
        avg_r = sum(rr) / len(rr) if rr else 0
        
        # Profit factor
        gross_profit = sum(r for r in rr if r > 0)
        gross_loss = abs(sum(r for r in rr if r < 0))
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Drawdown
        equity = [10000]
        for r in rr:
            equity.append(equity[-1] * (1 + r * 0.02))
        
        peak = max(equity)
        current = equity[-1]
        dd = (peak - current) / peak if peak > 0 else 0
        
        return RegimeMetrics(
            regime="",
            trade_count=total,
            win_rate=win_rate,
            profit_factor=pf,
            avg_r=avg_r,
            max_drawdown=dd
        )
    
    def run_analysis(
        self,
        trades: List[Dict]
    ) -> Dict[str, RegimeMetrics]:
        """Run regime robustness analysis."""
        by_regime = self.categorize_by_regime(trades)
        
        results = {}
        
        for regime, regime_trades in by_regime.items():
            metrics = self.calculate_regime_metrics(regime_trades)
            metrics.regime = regime
            results[regime] = metrics
        
        return results
    
    def assess_robustness(
        self,
        results: Dict[str, RegimeMetrics]
    ) -> Dict[str, Any]:
        """Assess regime robustness."""
        if not results:
            return {"status": "insufficient_data"}
        
        # Check for catastrophic failures
        failures = []
        
        for regime, metrics in results.items():
            if metrics.profit_factor < 0.8:
                failures.append(f"{regime}: PF={metrics.profit_factor:.2f}")
            
            if metrics.max_drawdown > 0.30:
                failures.append(f"{regime}: DD={metrics.max_drawdown:.0%}")
        
        is_robust = len(failures) == 0
        
        return {
            "is_robust": is_robust,
            "failures": failures,
            "regimes": {r: m.to_dict() for r, m in results.items()},
        }


# Regime Robustness Test End