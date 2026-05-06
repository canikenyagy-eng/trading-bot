"""
Data Feed Module - Event-Driven Market Data via ib_insync.
"""

import asyncio
from collections import deque
from dataclasses import dataclass, field
from typing import Optional
import logging
import ib_insync as ib
from ib_insync.ticker import Ticker

logger = logging.getLogger(__name__)


@dataclass
class TickData:
    """Lightweight tick data structure."""
    symbol: str
    bid: float = 0.0
    ask: float = 0.0
    last: float = 0.0
    volume: int = 0
    timestamp: float = 0.0
    
    @property
    def mid(self) -> float:
        if self.bid and self.ask:
            return (self.bid + self.ask) / 2
        return self.last
    
    @property
    def spread(self) -> float:
        if self.bid and self.ask:
            return self.ask - self.bid
        return 0.0


@dataclass
class BarData:
    """OHLC bar data."""
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: int = 0


class DataFeed:
    """Event-driven data feed using ib_insync."""
    
    def __init__(self, ib_client: 'IB', config: dict):
        self.ib = ib_client
        self.config = config
        self._contracts = {}
        self._tickers = {}
        self._tick_queues = {}
        self._subscribed = set()
        self._running = False
    
    def subscribe(self, symbol: str, sec_type: str = "CASH", exchange: str = "IDEALUSD"):
        """Subscribe to market data for symbol."""
        if symbol in self._subscribed:
            return
        
        contract = ib_contract(symbol, sec_type, exchange)
        
        # Request market data - returns ticker which hooks into events
        ticker = self.ib.reqMktData(contract, "", True, False)
        
        # Hook into the ticker's update event
        def on_tick(ticker):
            self._on_tick(ticker)
        
        ticker.updateEvent += on_tick
        
        self._contracts[symbol] = contract
        self._tick_queues[symbol] = deque(maxlen=self.config["data"]["tick_window"])
        self._subscribed.add(symbol)
        
        logger.info(f"Subscribed to {symbol}")
    
    def on_tick(self, ticker):
        """Handle tick update event - non-blocking."""
        try:
            # ticker can be tuple (tickerId, contract) or just ticker object
            if isinstance(ticker, tuple):
                ticker = ticker[0]
            
            symbol = getattr(ticker.contract, 'symbol', 'UNKNOWN') if ticker.contract else 'UNKNOWN'
            
            tick = TickData(
                symbol=symbol,
                bid=ticker.bid or 0.0,
                ask=ticker.ask or 0.0,
                last=ticker.last or 0.0,
                volume=ticker.volume or 0,
                timestamp=ticker.time or 0.0
            )
            
            self._tick_queues[symbol].append(tick)
        except Exception as e:
            pass
    
    def get_tick(self, symbol: str) -> Optional[TickData]:
        """Get latest tick."""
        if symbol in self._tick_queues and self._tick_queues[symbol]:
            return self._tick_queues[symbol][-1]
        return None
    
    def get_ticks(self, symbol: str, n: int = None) -> list:
        """Get tick window."""
        if symbol not in self._tick_queues:
            return []
        
        ticks = list(self._tick_queues[symbol])
        return ticks[-n:] if n else ticks
    
    def unsubscribe_all(self):
        """Unsubscribe from all."""
        for symbol in self._subscribed:
            self.ib.cancelMktData(101 + list(self._subscribed).index(symbol))
        
        self._subscribed.clear()
        logger.info("Unsubscribed from all")


def ib_contract(symbol: str, sec_type: str, exchange: str):
    """Create IB contract."""
    contract = ib.Contract()
    contract.symbol = symbol
    contract.secType = sec_type
    contract.exchange = exchange
    
    if sec_type == "CASH":
        contract.currency = symbol[3:] if len(symbol) > 3 else "USD"
    
    return contract