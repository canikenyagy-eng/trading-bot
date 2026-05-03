"""
Out-of-Sample Validation - Train/Test Split Validation.

Validates system performance on unseen data.
"""

from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from config import feature_flags as ff


@dataclass
class SplitResult:
    """Train/test split result."""
    
    period: str
    train_metrics: Dict[str, float]
    test_metrics: Dict[str, float]
    
    # Comparison
    wr_drop: float = 0.0
    pf_drop: float = 0.0
    is_stable: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "period": self.period,
            "train_metrics": self.train_metrics,
            "test_metrics": self.test_metrics,
            "wr_drop": self.wr_drop,
            "pf_drop": self.pf_drop,
            "is_stable": self.is_stable,
        }


class OutOfSampleValidator:
    """Out-of-sample validation engine."""
    
    def __init__(self):
        self.enabled = True
        
        # Split ratio
        self.train_ratio = 0.7
        self.test_ratio = 0.3
        
        # Stability threshold
        self.max_wr_drop = 0.15  # 15% max drop
        self.max_pf_drop = 0.30  # 30% max drop
    
    def split_data(
        self,
        trades: List[Dict],
        date_field: str = "timestamp"
    ) -> Tuple[List[Dict], List[Dict]]:
        """Split data into train/test.
        
        Args:
            trades: List of trade dicts
            date_field: Name of date field
            
        Returns:
            (train_trades, test_trades)
        """
        if not trades:
            return [], []
        
        # Sort by date
        sorted_trades = sorted(
            trades, 
            key=lambda t: t.get(date_field) or datetime.now()
        )
        
        split_idx = int(len(sorted_trades) * self.train_ratio)
        
        train = sorted_trades[:split_idx]
        test = sorted_trades[split_idx:]
        
        return train, test
    
    def calculate_metrics(self, trades: List[Dict]) -> Dict[str, float]:
        """Calculate performance metrics."""
        if not trades:
            return {"wr": 0, "pf": 0, "avg_r": 0, "dd": 0, "count": 0}
        
        wins = sum(1 for t in trades if t.get("result") == "tp")
        total = len(trades)
        
        win_rate = wins / total if total > 0 else 0
        
        # R values
        rr = [t.get("rr", 0) for t in trades]
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
        
        return {
            "win_rate": win_rate,
            "profit_factor": pf,
            "avg_r": avg_r,
            "max_drawdown": dd,
            "trade_count": total,
        }
    
    def run_validation(
        self,
        trades: List[Dict]
    ) -> SplitResult:
        """Run out-of-sample validation."""
        train, test = self.split_data(trades)
        
        train_metrics = self.calculate_metrics(train)
        test_metrics = self.calculate_metrics(test)
        
        # Calculate drops
        wr_drop = train_metrics["win_rate"] - test_metrics["win_rate"]
        pf_drop = train_metrics["profit_factor"] - test_metrics["profit_factor"]
        
        # Check stability
        is_stable = (
            wr_drop < self.max_wr_drop and
            pf_drop < self.max_pf_drop and
            test_metrics["profit_factor"] > 1.0
        )
        
        return SplitResult(
            period="70/30",
            train_metrics=train_metrics,
            test_metrics=test_metrics,
            wr_drop=wr_drop,
            pf_drop=pf_drop,
            is_stable=is_stable
        )
    
    def get_report(self) -> Dict[str, Any]:
        """Get validation report."""
        return {
            "train_ratio": self.train_ratio,
            "test_ratio": self.test_ratio,
            "stability_thresholds": {
                "max_wr_drop": self.max_wr_drop,
                "max_pf_drop": self.max_pf_drop,
            }
        }


# Out-of-Sample Validator End