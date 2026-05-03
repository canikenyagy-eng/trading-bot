"""
Portfolio Risk Control - Currency & Risk Management.

Tracks currency exposure and total risk to prevent stacking.
"""

from typing import Dict, List, Any
from dataclasses import dataclass, field
from collections import defaultdict

from config import feature_flags as ff


@dataclass
class CurrencyExposure:
    """Currency exposure tracking."""
    
    currency: str = ""
    long_exposure: float = 0.0
    short_exposure: float = 0.0
    net_exposure: float = 0.0
    risk_units: float = 0.0
    
    @property
    def total_exposure(self) -> float:
        return abs(self.long_exposure) + abs(self.short_exposure)


class PortfolioManager:
    """Portfolio risk management."""
    
    def __init__(self):
        self.enabled = ff.ENABLE_PORTFOLIO_CONTROL
        
        # Limits
        self.max_per_currency = 0.20  # 20% max per currency
        self.max_total_risk = 0.10    # 10% total risk
        self.max_correlation = 0.60  # Max correlation
        
        # Tracking
        self.currency_exposure: Dict[str, CurrencyExposure] = {}
        self.open_signals: List[Any] = []
        self.signal_history: List[Dict] = []
        
        # Currency pairs mapping
        self.currencies = {
            "EURUSD": "EUR", "GBPUSD": "GBP", "USDJPY": "JPY",
            "USDCHF": "CHF", "AUDUSD": "AUD", "USDCAD": "CAD",
            "NZDUSD": "NZD", "EURJPY": "EUR", "GBPJPY": "GBP",
        }
    
    def _get_currency(self, symbol: str) -> str:
        """Get base currency from symbol."""
        for pair, currency in self.currencies.items():
            if symbol.startswith(pair[:3]):
                return currency
        return symbol[:3]
    
    def register_signal(self, signal) -> None:
        """Register new signal."""
        if not self.enabled:
            return
        
        symbol = getattr(signal, 'symbol', '')
        direction = getattr(signal, 'direction', '')
        risk_percent = getattr(signal, 'risk_plan', {}).get('risk_percent', 0.02)
        
        currency = self._get_currency(symbol)
        
        if currency not in self.currency_exposure:
            self.currency_exposure[currency] = CurrencyExposure(currency=currency)
        
        exposure = self.currency_exposure[currency]
        
        if direction == 'long':
            exposure.long_exposure += risk_percent
        else:
            exposure.short_exposure += risk_percent
        
        exposure.net_exposure = exposure.long_exposure - exposure.short_exposure
        exposure.risk_units += risk_percent
        
        self.open_signals.append(signal)
    
    def close_signal(self, symbol: str, result: str) -> None:
        """Close signal and update exposure."""
        if not self.enabled:
            return
        
        # Find and remove signal
        for signal in self.open_signals:
            if signal.symbol == symbol:
                self.open_signals.remove(signal)
                
                direction = getattr(signal, 'direction', '')
                risk_percent = getattr(signal, 'risk_plan', {}).get('risk_percent', 0.02)
                
                currency = self._get_currency(symbol)
                if currency in self.currency_exposure:
                    exposure = self.currency_exposure[currency]
                    if direction == 'long':
                        exposure.long_exposure -= risk_percent
                    else:
                        exposure.short_exposure -= risk_percent
                    exposure.net_exposure = exposure.long_exposure - exposure.short_exposure
                break
    
    def get_exposure(self, currency: str) -> float:
        """Get currency exposure."""
        if currency not in self.currency_exposure:
            return 0.0
        return self.currency_exposure[currency].total_exposure
    
    def can_open(self, signal, penalty_only: bool = False) -> bool:
        """Check if can open new signal."""
        if not self.enabled:
            return True
        
        symbol = getattr(signal, 'symbol', '')
        direction = getattr(signal, 'direction', '')
        risk_percent = getattr(signal, 'risk_plan', {}).get('risk_percent', 0.02)
        
        currency = self._get_currency(symbol)
        
        # Check currency limit
        current = self.get_exposure(currency)
        if current + risk_percent > self.max_per_currency:
            return False
        
        # Check total risk
        total_risk = self.get_total_risk()
        if total_risk + risk_percent > self.max_total_risk:
            return False
        
        return True
    
    def get_penalty(self, signal) -> float:
        """Get position size penalty based on exposure."""
        if not self.enabled:
            return 0.0
        
        symbol = getattr(signal, 'symbol', '')
        currency = self._get_currency(symbol)
        
        exposure = self.get_exposure(currency)
        
        if exposure > self.max_per_currency * 0.8:
            return 0.2
        elif exposure > self.max_per_currency * 0.5:
            return 0.1
        
        return 0.0
    
    def get_total_risk(self) -> float:
        """Get total portfolio risk."""
        total = 0.0
        for exp in self.currency_exposure.values():
            total += exp.risk_units
        return total
    
    def get_report(self) -> Dict[str, Any]:
        """Get portfolio report."""
        return {
            "total_risk": self.get_total_risk(),
            "max_risk": self.max_total_risk,
            "open_signals": len(self.open_signals),
            "exposures": {
                currency: exp.total_exposure
                for currency, exp in self.currency_exposure.items()
            }
        }


# Portfolio Manager End