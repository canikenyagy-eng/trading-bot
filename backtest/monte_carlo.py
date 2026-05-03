"""
Monte Carlo Simulation - Risk Analysis.

Simulates trade outcomes to understand risk distribution.
"""

from typing import Dict, List, Any
from dataclasses import dataclass
import random


@dataclass
class MonteCarloResult:
    """Monte Carlo simulation result."""
    
    simulations: int
    metrics: Dict[str, Any]
    percentiles: Dict[str, float]
    risk_of_ruin: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulations": self.simulations,
            "metrics": self.metrics,
            "percentiles": self.percentiles,
            "risk_of_ruin": self.risk_of_ruin,
        }


class MonteCarloSimulator:
    """Monte Carlo simulation engine."""
    
    def __init__(self):
        self.enabled = True
        
        # Simulation settings
        self.simulations = 1000
        self.initial_capital = 10000
        self.risk_per_trade = 0.02
    
    def simulate(
        self,
        trades: List[Dict],
        simulations: int = None
    ) -> MonteCarloResult:
        """Run Monte Carlo simulation.
        
        Args:
            trades: Historical trades
            simulations: Number of simulations
            
        Returns:
            MonteCarloResult
        """
        n_sims = simulations or self.simulations
        
        # Get trade statistics
        rr_values = [t.get("rr", 0) for t in trades if "rr" in t]
        
        if not rr_values:
            return MonteCarloResult(
                simulations=0,
                metrics={},
                percentiles={},
                risk_of_ruin=1.0
            )
        
        win_rate = sum(1 for r in rr_values if r > 0) / len(rr_values)
        
        results = []
        
        for _ in range(n_sims):
            # Simulate random trade sequence
            capital = self.initial_capital
            
            for _ in range(len(trades)):
                won = random.random() < win_rate
                
                if won:
                    # Random R
                    r = random.choice([r for r in rr_values if r > 0])
                else:
                    r = -1.0  # Assume 1R loss
                
                capital *= (1 + r * self.risk_per_trade)
                
                # Check ruin
                if capital < self.initial_capital * 0.5:
                    break
            
            results.append(capital)
        
        # Calculate metrics
        final_values = results
        avg_return = sum(final_values) / len(final_values) / self.initial_capital - 1
        
        # Percentiles
        sorted_results = sorted(final_values)
        p10 = sorted_results[int(len(sorted_results) * 0.1)]
        p50 = sorted_results[int(len(sorted_results) * 0.5)]
        p90 = sorted_results[int(len(sorted_results) * 0.9)]
        
        # Risk of ruin (ending below 50% of initial)
        ruin_count = sum(1 for v in final_values if v < self.initial_capital * 0.5)
        risk_of_ruin = ruin_count / len(final_values)
        
        return MonteCarloResult(
            simulations=n_sims,
            metrics={
                "avg_return": avg_return,
                "min_return": min(final_values) / self.initial_capital - 1,
                "max_return": max(final_values) / self.initial_capital - 1,
            },
            percentiles={
                "p10": p10 / self.initial_capital - 1,
                "p50": p50 / self.initial_capital - 1,
                "p90": p90 / self.initial_capital - 1,
            },
            risk_of_ruin=risk_of_ruin
        )
    
    def get_worst_case(
        self,
        trades: List[Dict]
    ) -> Dict[str, float]:
        """Get worst-case scenarios."""
        result = self.simulate(trades, 1000)
        
        return {
            "worst_10pct": result.percentiles["p10"],
            "risk_of_ruin": result.risk_of_ruin,
        }


# Monte Carlo Simulator End