"""
Production-Grade Live Runner for Trading Intelligence Engine.

Main entry point for continuous real-time signal generation.
"""

import asyncio
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/runtime.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """System configuration."""
    
    # Symbols to analyze
    SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]
    
    # Timeframe
    TIMEFRAME = "H1"
    
    # Loop settings
    LOOP_INTERVAL = 300  # seconds (5 min)
    START_HOUR = 6   # Start processing hour (UTC)
    END_HOUR = 22  # End processing hour
    
    # Signal settings
    MIN_SIGNAL_QUALITY = 0.4
    COOLDOWN_SECONDS = 600  # 10 min between same symbol
    MAX_SIGNALS_PER_HOUR = 3
    
    # Data settings
    REQUIRED_BARS = 200
    
    # Telegram (use environment variables)
    @property
    def TELEGRAM_TOKEN(self) -> str:
        return os.environ.get("TELEGRAM_TOKEN", "")
    
    @property
    def TELEGRAM_CHAT_ID(self) -> str:
        return os.environ.get("TELEGRAM_CHAT_ID", "")
    
    # System mode
    SYSTEM_MODE = "NORMAL"  # NORMAL, DEFENSIVE, CONSERVATIVE, HALT
    
    # Feature flags
    ENABLE_SHORT_SIGNALS = True
    ENABLE_FULL_SIGNALS = True


# ============================================================================
# DATA INGESTION LAYER
# ============================================================================

class DataIngestion:
    """Market data ingestion from MT5 or simulation."""
    
    def __init__(self, config: Config):
        self.config = config
        self.mt5_available = False
        self._init_mt5()
    
    def _init_mt5(self):
        """Initialize MT5 connection."""
        try:
            import MetaTrader5 as mt5
            self.mt5 = mt5
            self.mt5.initialize()
            self.mt5_available = True
            logger.info("MetaTrader5 connected")
        except Exception as e:
            logger.warning(f"MT5 not available: {e}. Using simulation mode.")
            self.mt5_available = False
    
    def fetch_data(self, symbol: str, timeframe: str, bars: int) -> Optional[Dict]:
        """Fetch OHLCV data for symbol."""
        if self.mt5_available:
            return self._fetch_mt5(symbol, timeframe, bars)
        else:
            return self._generate_simulated_data(symbol, bars)
    
    def _fetch_mt5(self, symbol: str, timeframe: str, bars: int) -> Optional[Dict]:
        """Fetch real data from MT5."""
        try:
            # Map timeframe
            tf_map = {
                "M1": self.mt5.TIMEFRAME_M1,
                "M5": self.mt5.TIMEFRAME_M5,
                "M15": self.mt5.TIMEFRAME_M15,
                "M30": self.mt5.TIMEFRAME_M30,
                "H1": self.mt5.TIMEFRAME_H1,
                "H4": self.mt5.TIMEFRAME_H4,
                "D1": self.mt5.TIMEFRAME_D1,
            }
            
            mt5_tf = tf_map.get(timeframe, self.mt5.TIMEFRAME_H1)
            
            rates = self.mt5.copy_rates_from_pos(symbol, mt5_tf, 0, bars)
            
            if not rates or len(rates) < bars:
                logger.warning(f"Insufficient data for {symbol}")
                return None
            
            # Extract arrays
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "opens": [r[1] for r in rates],
                "highs": [r[2] for r in rates],
                "lows": [r[3] for r in rates],
                "closes": [r[4] for r in rates],
                "volumes": [r[5] for r in rates],
                "bid": self.mt5.symbol_info_tick(symbol).bid,
                "ask": self.mt5.symbol_info_tick(symbol).ask,
            }
            
        except Exception as e:
            logger.error(f"MT5 fetch error for {symbol}: {e}")
            return None
    
    def _generate_simulated_data(self, symbol: str, bars: int) -> Dict:
        """Generate simulated market data for testing."""
        import random
        
        # Base prices
        base_prices = {
            "EURUSD": 1.0850,
            "GBPUSD": 1.2650,
            "USDJPY": 149.50,
            "XAUUSD": 2020.0,
        }
        
        base = base_prices.get(symbol, 1.0)
        
        # Generate realistic price movement
        prices = []
        current = base
        
        for _ in range(bars):
            change = random.gauss(0, base * 0.002)
            current += change
            prices.append(current)
        
        # Generate OHLC
        opens = prices[:-1]
        closes = prices[1:]
        
        highs = [max(o, c) * (1 + random.gauss(0, 0.001)) for o, c in zip(opens, closes)]
        lows = [min(o, c) * (1 - random.gauss(0, 0.001)) for o, c in zip(opens, closes)]
        
        return {
            "symbol": symbol,
            "timeframe": self.config.TIMEFRAME,
            "opens": opens,
            "highs": highs,
            "lows": lows,
            "closes": closes,
            "volumes": [random.randint(100, 1000) for _ in range(len(opens))],
            "bid": closes[-1] - 0.0001,
            "ask": closes[-1] + 0.0001,
        }
    
    def check_connection(self) -> bool:
        """Check MT5 connection status."""
        if not self.mt5_available:
            return True  # Simulation mode is always "connected"
        
        try:
            return self.mt5.terminal_info() is not None
        except:
            return False


# ============================================================================
# SIGNAL PROCESSOR
# ============================================================================

class SignalProcessor:
    """Process market data into signals."""
    
    def __init__(self, config: Config):
        self.config = config
        
        # Import pipeline
        try:
            from pipeline.integrated_pipeline import IntegratedPipeline
            self.pipeline = IntegratedPipeline()
            self.pipeline_available = True
        except Exception as e:
            logger.error(f"Pipeline import failed: {e}")
            self.pipeline_available = False
    
    def process(self, data: Dict) -> Optional[Dict]:
        """Process market data into signal."""
        if not self.pipeline_available:
            return None
        
        try:
            # Add regime detection (simplified)
            regime = self._detect_regime(data)
            
            # Process through pipeline
            result = self.pipeline.process_signal(data, regime=regime)
            
            return result
            
        except Exception as e:
            logger.error(f"Signal processing error: {e}")
            return None
    
    def _detect_regime(self, data: Dict) -> str:
        """Detect market regime."""
        closes = data.get("closes", [])
        
        if len(closes) < 50:
            return "trend"
        
        # Simple regime detection
        recent = closes[-20:]
        first = recent[0]
        last = recent[-1]
        
        # Uptrend
        if last > first * 1.005:
            return "trend_up"
        
        # Downtrend
        if last < first * 0.995:
            return "trend_down"
        
        return "range"


# ============================================================================
# SIGNAL MANAGER
# ============================================================================

class SignalManager:
    """Manage signal flow and filtering."""
    
    def __init__(self, config: Config):
        self.config = config
        
        # Signal cache
        self.last_signals: Dict[str, float] = {}  # symbol -> timestamp
        self.signal_cache: Dict[str, Dict] = {}  # symbol -> signal data
        
        # History (for health monitoring)
        self.recent_results: List[Dict] = []
        self.total_signals = 0
        self.total_sent = 0
    
    def should_send(self, signal: Dict) -> bool:
        """Check if signal should be sent."""
        if not signal:
            return False
        
        symbol = signal.get("symbol", "")
        
        # Check quality
        if signal.get("confidence", 0) < self.config.MIN_SIGNAL_QUALITY:
            return False
        
        # Check cooldown
        last_time = self.last_signals.get(symbol, 0)
        if time.time() - last_time < self.config.COOLDOWN_SECONDS:
            return False
        
        # Check mode
        mode = self.config.SYSTEM_MODE
        if mode == "HALT":
            return False
        
        return True
    
    def record_signal(self, signal: Dict) -> None:
        """Record signal for tracking."""
        symbol = signal.get("symbol", "")
        self.last_signals[symbol] = time.time()
        self.signal_cache[symbol] = signal
        self.total_signals += 1
    
    def record_result(self, won: bool, rr: float = 0.0) -> None:
        """Record trade result."""
        self.recent_results.append({
            "won": won,
            "rr": rr,
            "timestamp": time.time()
        })
        
        # Keep only last 50
        if len(self.recent_results) > 50:
            self.recent_results.pop(0)
    
    def get_health(self) -> Dict:
        """Get system health metrics."""
        if not self.recent_results:
            return {
                "signals": 0,
                "sent": 0,
                "winrate": 0,
            }
        
        recent = self.recent_results[-20:]
        wins = sum(1 for r in recent if r.get("won", False))
        
        return {
            "signals": self.total_signals,
            "sent": self.total_sent,
            "winrate": wins / len(recent) if recent else 0,
        }


# ============================================================================
# TELEGRAM SENDER
# ============================================================================

class TelegramSender:
    """Send signals to Telegram."""
    
    def __init__(self, config: Config):
        self.config = config
        
        self.bot = None
        self._init_bot()
    
    def _init_bot(self):
        """Initialize Telegram bot."""
        try:
            from telegram import Bot
            token = self.config.TELEGRAM_TOKEN
            
            if token:
                self.bot = Bot(token=token)
                self.bot_available = True
                logger.info("Telegram bot initialized")
            else:
                logger.warning("Telegram token not configured")
                self.bot_available = False
                
        except Exception as e:
            logger.error(f"Telegram init error: {e}")
            self.bot_available = False
    
    async def send(self, message: str, mode: str = "short") -> bool:
        """Send message to Telegram."""
        if not self.bot_available:
            logger.info(f"[SIMULATION] Would send: {message[:100]}...")
            return True
        
        try:
            chat_id = self.config.TELEGRAM_CHAT_ID
            
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="HTML"
            )
            
            logger.info(f"Signal sent ({mode})")
            return True
            
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False


# ============================================================================
# MAIN LIVE RUNNER
# ============================================================================

class LiveRunner:
    """Main live execution engine."""
    
    def __init__(self):
        # Configuration
        self.config = Config()
        
        # Components
        self.data_ingestion = DataIngestion(self.config)
        self.signal_processor = SignalProcessor(self.config)
        self.signal_manager = SignalManager(self.config)
        self.telegram_sender = TelegramSender(self.config)
        
        # Stats
        self.start_time = time.time()
        self.iterations = 0
        
        # Formatter
        self._init_formatter()
    
    def _init_formatter(self):
        """Initialize signal formatter."""
        try:
            from analytics.telegram_formatter import SignalFormatter
            self.formatter = SignalFormatter(
                verbose=self.config.ENABLE_FULL_SIGNALS,
                use_html=True
            )
        except:
            self.formatter = None
    
    async def run(self):
        """Main event loop."""
        logger.info("="*60)
        logger.info("TRADING INTELLIGENCE ENGINE - LIVE MODE")
        logger.info("="*60)
        logger.info(f"Symbols: {self.config.SYMBOLS}")
        logger.info(f"Interval: {self.config.LOOP_INTERVAL}s")
        logger.info(f"Mode: {self.config.SYSTEM_MODE}")
        logger.info("="*60)
        
        while True:
            try:
                # Check MT5 connection
                if not self.data_ingestion.check_connection():
                    logger.warning("MT5 disconnected, using simulation")
                
                # Process each symbol
                for symbol in self.config.SYMBOLS:
                    await self._process_symbol(symbol)
                
                # Log health
                self._log_health()
                
                # Wait
                await asyncio.sleep(self.config.LOOP_INTERVAL)
                self.iterations += 1
                
            except KeyboardInterrupt:
                logger.info("Stopped by user")
                break
            except Exception as e:
                logger.error(f"Loop error: {e}")
                await asyncio.sleep(10)
    
    async def _process_symbol(self, symbol: str):
        """Process single symbol."""
        # Fetch data
        data = self.data_ingestion.fetch_data(
            symbol,
            self.config.TIMEFRAME,
            self.config.REQUIRED_BARS
        )
        
        if not data:
            logger.debug(f"No data for {symbol}")
            return
        
        # Process signal
        signal = self.signal_processor.process(data)
        
        if not signal:
            return
        
        # Add symbol
        signal["symbol"] = symbol
        
        # Check if should send
        if not self.signal_manager.should_send(signal):
            return
        
        # Record
        self.signal_manager.record_signal(signal)
        self.signal_manager.total_sent += 1
        
        # Format message
        if self.formatter:
            message = self.formatter.format_signal(signal)
        else:
            message = self._format_simple_signal(signal)
        
        # Send to Telegram
        mode = "short" if self.config.ENABLE_SHORT_SIGNALS else "full"
        await self.telegram_sender.send(message, mode)
    
    def _format_simple_signal(self, signal: Dict) -> str:
        """Format simple signal message."""
        lines = [
            f"📊 {signal.get('symbol', 'UNKNOWN')}",
            f"Direction: {signal.get('direction', 'N/A')}",
            f"Confidence: {signal.get('confidence', 0):.0%}",
            f"Grade: {signal.get('setup_grade', 'N/A')}",
        ]
        
        if signal.get("entry"):
            lines.append(f"Entry: {signal.get('entry')}")
            lines.append(f"SL: {signal.get('sl', 'N/A')}")
        
        return "\n".join(lines)
    
    def _log_health(self):
        """Log system health."""
        health = self.signal_manager.get_health()
        
        runtime = time.time() - self.start_time
        hours = runtime / 3600
        
        logger.info(
            f"[{self.iterations}] Mode: {self.config.SYSTEM_MODE} | "
            f"Signals: {health['signals']} | "
            f"Sent: {health['sent']} | "
            f"WR: {health['winrate']:.0%} | "
            f"Runtime: {hours:.1f}h"
        )


# ============================================================================
# ENTRY POINT
# ============================================================================

async def main():
    """Main entry point."""
    runner = LiveRunner()
    await runner.run()


if __name__ == "__main__":
    # Create logs directory
    os.makedirs("logs", exist_ok=True)
    
    # Run
    asyncio.run(main())