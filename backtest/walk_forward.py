"""
Walk-Forward Analysis - Rolling Window Validation.

Validates system with rolling train/test windows.
"""

from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from backtest.oos_validation import OutOfSampleValidator


@dataclass
class WindowResult:
    """Rolling window result."""
    
    train_period: str
    test_period: str
    metrics: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "train_period": self.train_period,
            "test_period": self.test_period,
            "metrics": self.metrics,
        }


class WalkForwardValidator:
    """Walk-forward validation engine."""
    
    def __init__(self):
        self.enabled = True
        
        # Window configuration
        self.train_months = 3
        self.test_months = 1
        self.step_months = 1
        
        self.validator = OutOfSampleValidator()
    
    def run_analysis(
        self,
        trades: List[Dict]
    ) -> List[WindowResult]:
        """Run walk-forward analysis.
        
        Args:
            trades: List of trade dicts with timestamps
            
        Returns:
            List of window results
        """
        if not trades:
            return []
        
        # Sort by date
        sorted_trades = sorted(trades, key=lambda t: t.get("timestamp", datetime.now()))
        
        # Get date range
        dates = [t.get("timestamp", datetime.now()) for t in sorted_trades]
        min_date = min(dates)
        max_date = max(dates)
        
        results = []
        current = min_date
        
        while current < max_date:
            train_end = current + timedelta(days=self.train_months * 30)
            test_end = train_end + timedelta(days=self.test_months * 30)
            
            # Get window trades
            train_trades = [t for t in sorted_trades 
                          if current <= t.get("timestamp", datetime.now()) < train_end]
            test_trades = [t for t in sorted_trades 
                         if train_end <= t.get("timestamp", datetime.now()) < test_end]
            
            if len(train_trades) >= 10 and len(test_trades) >= 5:
                # Calculate metrics
                train_metrics = self.validator.calculate_metrics(train_trades)
                test_metrics = self.validator.calculate_metrics(test_trades)
                
                results.append(WindowResult(
                    train_period=f"{current.strftime('%Y-%m')}",
                    test_period=f"{train_end.strftime('%Y-%m')}",
                    metrics=test_metrics
                ))
            
            current += timedelta(days=self.step_months * 30)
        
        return results
    
    def calculate_rolling_metrics(
        self,
        results: List[WindowResult]
    ) -> Dict[str, float]:
        """Calculate rolling metrics."""
        if not results:
            return {}
        
        wr_values = [r.metrics.get("win_rate", 0) for r in results]
        pf_values = [r.metrics.get("profit_factor", 0) for r in results]
        dd_values = [r.metrics.get("max_drawdown", 0) for r in results]
        
        return {
            "avg_winrate": sum(wr_values) / len(wr_values),
            "avg_profit_factor": sum(pf_values) / len(pf_values),
            "avg_drawdown": sum(dd_values) / len(dd_values),
            "min_winrate": min(wr_values),
            "min_pf": min(pf_values),
            "max_drawdown": max(dd_values),
            "windows": len(results),
        }
    
    def get_stability_assessment(
        self,
        results: List[WindowResult]
    ) -> Dict[str, Any]:
        """Assess stability across windows."""
        if not results:
            return {"status": "insufficient_data"}
        
        metrics = self.calculate_rolling_metrics(results)
        
        # Check stability
        wr_variance = self._variance([r.metrics.get("win_rate", 0) for r in results])
        pf_variance = self._variance([r.metrics.get("profit_factor", 0) for r in results])
        
        is_stable = (
            wr_variance < 0.02 and
            pf_variance < 0.5 and
            metrics.get("min_pf", 0) > 0.8
        )
        
        return {
            "is_stable": is_stable,
            "wr_variance": wr_variance,
            "pf_variance": pf_variance,
            "metrics": metrics,
        }
    
    def _variance(self, values: List[float]) -> float:
        """Calculate variance."""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        return sum((v - mean) ** 2 for v in values) / len(values)


# Walk-Forward Validator End