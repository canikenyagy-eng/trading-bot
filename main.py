"""
IB Trading System - Main Entry Point.
Event-driven architecture with ib_insync.
"""

import asyncio
import json
import logging
import signal as sys_signal
import sys
from logging.handlers import RotatingFileHandler

import ib_insync as ib

from data_feed import DataFeed
from strategy import Strategy
from execution import Execution
from risk_management import RiskManager


class TradingSystem:
    """Main trading system."""
    
    def __init__(self, config_file: str = "config/config.json"):
        self._load_config(config_file)
        self._setup_logging()
        
        self.ib = ib.IB()
        self.data_feed = None
        self.strategy = None
        self.execution = None
        self.risk = None
        
        self._running = False
        self._tasks = []
    
    def _load_config(self, config_file: str):
        """Load configuration."""
        with open(config_file) as f:
            self.config = json.load(f)
    
    def _setup_logging(self):
        """Setup logging."""
        logger = logging.getLogger()
        logger.setLevel(self.config["logging"]["level"])
        
        handler = RotatingFileHandler(
            self.config["logging"]["file"],
            maxBytes=self.config["logging"]["max_bytes"],
            backupCount=self.config["logging"]["backup_count"]
        )
        
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        
        self.logger = logger
    
    def connect(self):
        """Connect to IB Gateway."""
        port = self.config["ib"]["paper_port"]
        
        self.ib.connect(
            self.config["ib"]["host"],
            port,
            self.config["ib"]["client_id"]
        )
        
        self.logger.info(f"Connected to IB port {port}")
        
        self._setup_components()
    
    def _setup_components(self):
        """Setup system components."""
        self.data_feed = DataFeed(self.ib, self.config)
        self.strategy = Strategy(self.config, self.data_feed)
        self.execution = Execution(self.ib, self.config)
        self.risk = RiskManager(self.config)
        
        all_symbols = (
            self.config["symbols"]["forex"] +
            self.config["symbols"]["metals"] +
            self.config["symbols"]["crypto"]
        )
        
        for symbol in all_symbols:
            self.data_feed.subscribe(symbol)
            self.strategy.add_symbol(symbol)
        
        self.ib.tickEvent += self._on_tick
        self.ib.orderEvent += self._on_order
    
    def _on_tick(self, ticker):
        """Handle tick event."""
        self.data_feed.on_tick(ticker)
        
        symbol = ticker.contract.symbol
        
        tick = self.data_feed.get_tick(symbol)
        
        if tick:
            sig = self.strategy.on_tick(symbol, tick)
            
            if sig and sig.direction != "FLAT":
                self._process_signal(sig)
    
    def _on_order(self, order):
        """Handle order event."""
        self.execution.on_order_status(
            order.orderId,
            order.status,
            order.filled,
            order.avgFillPrice
        )
    
    def _process_signal(self, sig):
        """Process trading signal."""
        if not sig or sig.direction == "FLAT":
            return
        
        quantity = self._calculate_size(sig)
        
        if quantity == 0:
            return
        
        if not self.risk.check_position_size(sig.symbol, quantity):
            return
        
        asyncio.create_task(
            self.execution.submit_order(
                sig.symbol,
                sig.direction,
                quantity
            )
        )
    
    def _calculate_size(self, sig) -> int:
        """Calculate position size."""
        balance = 100000
        risk = self.config["risk"]["stop_loss_pct"]
        
        return int(balance * risk / sig.price)
    
    def run(self):
        """Run system."""
        self._running = True
        
        self.logger.info("="*50)
        self.logger.info("TRADING SYSTEM STARTED")
        self.logger.info("="*50)
        
        sys_signal.signal(sys_signal.SIGINT, self._shutdown)
        sys_signal.signal(sys_signal.SIGTERM, self._shutdown)
        
        self.ib.run()
    
    def _shutdown(self, signum, frame):
        """Graceful shutdown."""
        self.logger.info("Shutdown initiated...")
        
        self._running = False
        
        if self.data_feed:
            self.data_feed.unsubscribe_all()
        
        self.ib.disconnect()
        
        self.logger.info("System stopped")
        
        sys.exit(0)


def main():
    """Main entry point."""
    system = TradingSystem()
    
    try:
        system.connect()
        system.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Fatal error: {e}")


if __name__ == "__main__":
    main()