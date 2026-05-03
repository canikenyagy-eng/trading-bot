"""
Validation Runner - Unified Validation Engine.

Runs all validation tests and generates comprehensive report.
"""

from typing import Dict, List, Any
from dataclasses import dataclass

from backtest.oos_validation import OutOfSampleValidator
from backtest.walk_forward import WalkForwardValidator
from backtest.monte_carlo import MonteCarloSimulator
from backtest.regime_robustness import RegimeRobustnessTest
from backtest.feature_ablation import FeatureAblationTest
from analytics.true_calibration import TrueCalibration


@dataclass
class ValidationReport:
    """Comprehensive validation report."""
    
    is_valid: bool
    summary: Dict[str, Any]
    oos_result: Dict
    walk_forward: Dict
    monte_carlo: Dict
    regime_robustness: Dict
    ablation: List
    calibration: Dict


class ValidationRunner:
    """Unified validation runner."""
    
    def __init__(self):
        # Validators
        self.oos = OutOfSampleValidator()
        self.walk_forward = WalkForwardValidator()
        self.monte_carlo = MonteCarloSimulator()
        self.regime = RegimeRobustnessTest()
        self.ablation = FeatureAblationTest()
        self.calibration = TrueCalibration()
    
    def run_full_validation(
        self,
        trades: List[Dict]
    ) -> ValidationReport:
        """Run full validation suite."""
        
        # 1. Out-of-sample
        oos_result = self.oos.run_validation(trades)
        
        # 2. Walk-forward
        wf_results = self.walk_forward.run_analysis(trades)
        wf_metrics = self.walk_forward.calculate_rolling_metrics(wf_results)
        wf_stability = self.walk_forward.get_stability_assessment(wf_results)
        
        # 3. Monte Carlo
        mc_result = self.monte_carlo.simulate(trades)
        
        # 4. Regime robustness
        regime_results = self.regime.run_analysis(trades)
        regime_assessment = self.regime.assess_robustness(regime_results)
        
        # 5. Feature ablation
        ablation_results = self.ablation.run_full_analysis(trades)
        ablation_ranking = self.ablation.get_feature_ranking(ablation_results)
        
        # 6. Calibration
        for trade in trades:
            score = trade.get("confidence", 0.5)
            won = trade.get("result") == "tp"
            self.calibration.record_outcome(score, won)
        
        calibration_report = self.calibration.get_calibration_report()
        
        # Determine validity
        is_valid = (
            oos_result.is_stable and
            mc_result.risk_of_ruin < 0.1 and
            regime_assessment.get("is_robust", False) and
            calibration_report.get("calibration_error", 1) < 0.1
        )
        
        return ValidationReport(
            is_valid=is_valid,
            summary={
                "total_trades": len(trades),
                "validation_passed": is_valid,
            },
            oos_result=oos_result.to_dict(),
            walk_forward={
                "metrics": wf_metrics,
                "stability": wf_stability,
                "windows": len(wf_results),
            },
            monte_carlo=mc_result.to_dict(),
            regime_robustness=regime_assessment,
            ablation=ablation_ranking,
            calibration=calibration_report,
        )
    
    def print_report(self, report: ValidationReport) -> None:
        """Print validation report."""
        
        print("="*70)
        print("📊 VALIDATION REPORT")
        print("="*70)
        
        print(f"\n✅ VALIDATION: {'PASSED' if report.is_valid else 'FAILED'}")
        
        print(f"\n📈 OUT-OF-SAMPLE:")
        oos = report.oos_result
        print(f"   Train: WR={oos['train_metrics']['win_rate']:.1%}, PF={oos['train_metrics']['profit_factor']:.2f}")
        print(f"   Test:  WR={oos['test_metrics']['win_rate']:.1%}, PF={oos['test_metrics']['profit_factor']:.2f}")
        print(f"   Drop:  WR={oos['wr_drop']:.1%}, PF={oos['pf_drop']:.2f}")
        
        print(f"\n📈 WALK-FORWARD:")
        wf = report.walk_forward
        print(f"   Windows: {wf['windows']}")
        print(f"   Avg WR: {wf['metrics'].get('avg_winrate', 0):.1%}")
        print(f"   Avg PF: {wf['metrics'].get('avg_profit_factor', 0):.2f}")
        
        print(f"\n📈 MONTE CARLO:")
        mc = report.monte_carlo
        print(f"   Sims: {mc['simulations']}")
        print(f"   Risk of Ruin: {mc['risk_of_ruin']:.1%}")
        
        print(f"\n📈 REGIME ROBUSTNESS:")
        rr = report.regime_robustness
        print(f"   Robust: {rr.get('is_robust', False)}")
        
        print(f"\n📈 FEATURE ABLATION:")
        for a in report.ablation[:3]:
            print(f"   {a['feature']}: contribution={a['contribution']:.3f}")
        
        print(f"\n📈 CALIBRATION:")
        cal = report.calibration
        print(f"   Error: {cal.get('calibration_error', 'N/A')}")
        
        print()


# Validation Runner End