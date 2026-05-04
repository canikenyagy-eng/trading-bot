"""
Simple Live Runner - Trading Intelligence Engine

Simplified version for testing without complex dependencies.
"""

import asyncio
import os
import sys
import time
import random
from datetime import datetime
from typing import Dict, List, Any

# Setup
os.makedirs("logs", exist_ok=True)

print("="*60)
print("TRADING INTELLIGENCE ENGINE - SIMPLE MODE")
print("="*60)

# ============================================================================
# CONFIG
# ============================================================================

class Config:
    """Simple configuration."""
    
    # Symbols
    SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]
    
    # Settings
    TIMEFRAME = "H1"
    LOOP_INTERVAL = 60  # 1 minute for testing
    COOLDOWN = 300  # 5 minutes
    
    # Signal quality
    MIN_CONFIDENCE = 0.4
    
    # Telegram - hardcoded for testing, or from environment
    TOKEN = os.environ.get("TELEGRAM_TOKEN", "8608494961:AAGHrERt8b4MIgTWeaqg-Qn3K-XNo6GzZAQ")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "1916051263")


# ============================================================================
# DATA - REAL MARKET DATA
# ============================================================================

def get_market_data(symbol: str, bars: int = 100) -> Dict:
    """Get real market data from Yahoo Finance."""
    
    # Yahoo Finance symbols
    symbol_map = {
        "EURUSD": "EURUSD=X",
        "GBPUSD": "GBPUSD=X",
        "USDJPY": "JPY=X",
        "XAUUSD": "GC=F",  # Gold futures
    }
    
    yahoo_symbol = symbol_map.get(symbol, symbol + "=X")
    
    try:
        import yfinance as yf
        
        ticker = yf.Ticker(yahoo_symbol)
        data = ticker.history(period="5d", interval="1h")
        
        if data.empty:
            return generate_market_data(symbol, bars)
        
        return {
            "symbol": symbol,
            "timeframe": "H1",
            "opens": data["Open"].tolist()[-bars:],
            "highs": data["High"].tolist()[-bars:],
            "lows": data["Low"].tolist()[-bars:],
            "closes": data["Close"].tolist()[-bars:],
            "volumes": data["Volume"].tolist()[-bars:],
            "bid": data["Close"].iloc[-1] - 0.0001,
            "ask": data["Close"].iloc[-1] + 0.0001,
        }
        
    except Exception as e:
        print(f"  ⚠️  Data error for {symbol}: {e}")
        return generate_market_data(symbol, bars)


def generate_market_data(symbol: str, bars: int = 100) -> Dict:
    """Fallback: generate simulated market data."""
    
    # Base prices
    base_prices = {
        "EURUSD": 1.0850,
        "GBPUSD": 1.2650,
        "USDJPY": 149.50,
        "XAUUSD": 2020.0,
    }
    
    base = base_prices.get(symbol, 1.0)
    
    # Generate prices
    prices = [base]
    for _ in range(bars - 1):
        change = random.gauss(0, base * 0.002)
        prices.append(prices[-1] + change)
    
    # Generate OHLC
    opens = prices[:-1]
    closes = prices[1:]
    highs = [max(o, c) * (1 + abs(random.gauss(0, 0.0005))) for o, c in zip(opens, closes)]
    lows = [min(o, c) * (1 - abs(random.gauss(0, 0.0005))) for o, c in zip(opens, closes)]
    
    return {
        "symbol": symbol,
        "timeframe": "H1",
        "opens": opens,
        "highs": highs,
        "lows": lows,
        "closes": closes,
        "volumes": [random.randint(100, 1000) for _ in range(len(opens))],
        "bid": closes[-1] - 0.0001,
        "ask": closes[-1] + 0.0001,
    }


# ============================================================================
# SIGNAL GENERATOR
# ============================================================================

def generate_signal(data: Dict) -> Dict:
    """Generate a signal from market data."""
    
    closes = data.get("closes", [])
    if len(closes) < 20:
        return {}
    
    # Simple analysis
    recent = closes[-20:]
    
    # Trend detection
    first = recent[0]
    last = recent[-1]
    change = (last - first) / first
    
    # Determine direction
    if change > 0.003:
        direction = "LONG"
    elif change < -0.003:
        direction = "SHORT"
    else:
        direction = "NEUTRAL"
    
    # Calculate confidence (simplified)
    confidence = min(0.9, max(0.3, 0.5 + change * 10))
    
    # Entry points
    entry = data.get("closes", [0])[-1]
    
    # Simple RR
    if direction == "LONG":
        sl = entry - (entry * 0.002)
        tp1 = entry + (entry * 0.006)
        tp2 = entry + (entry * 0.010)
    elif direction == "SHORT":
        sl = entry + (entry * 0.002)
        tp1 = entry - (entry * 0.006)
        tp2 = entry - (entry * 0.010)
    else:
        sl = entry
        tp1 = entry
        tp2 = entry
    
    # Generate grade
    if confidence > 0.7:
        grade = "A+"
    elif confidence > 0.55:
        grade = "A"
    elif confidence > 0.45:
        grade = "B"
    else:
        grade = "C"
    
    return {
        "symbol": data.get("symbol"),
        "direction": direction,
        "entry": round(entry, 4),
        "sl": round(sl, 4),
        "tp1": round(tp1, 4),
        "tp2": round(tp2, 4),
        "confidence": confidence,
        "setup_grade": grade,
        "regime": "trend" if abs(change) > 0.003 else "range",
    }


# ============================================================================
# TELEGRAM
# ============================================================================

async def send_telegram(message: str, config: Config):
    """Send message to Telegram."""
    if not config.TOKEN or not config.CHAT_ID:
        print(f"[SIMULATION] {message[:80]}...")
        return
    
    try:
        # Use subprocess to avoid local telegram package conflict
        import subprocess
        import json
        
        # Create a temporary script to send message
        script = f'''
import asyncio
from telegram import Bot

async def main():
    bot = Bot(token="{config.TOKEN}")
    await bot.send_message(
        chat_id="{config.CHAT_ID}",
        text={repr(message)},
        parse_mode="HTML"
    )

asyncio.run(main())
'''
        
        result = subprocess.run(
            ['python3', '-c', script],
            capture_output=True,
            text=True,
            cwd='/tmp'  # Run from /tmp to avoid local telegram folder
        )
        
        if result.returncode == 0:
            print(f"✅ Sent to Telegram!")
        else:
            print(f"❌ Error: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Telegram error: {e}")


# ============================================================================
# FORMATTER
# ============================================================================

def format_signal_short(signal: Dict) -> str:
    """Format signal as short message."""
    if not signal:
        return ""
    
    emoji = "🟢" if signal["direction"] == "LONG" else "🔴"
    
    return f"""
{emoji} *{signal['symbol']}* {signal['direction']}

Entry: {signal['entry']}
SL: {signal['sl']}
TP: {signal['tp1']}

Confidence: {signal['confidence']:.0%}
Grade: {signal['setup_grade']}
"""


def format_signal_full(signal: Dict) -> str:
    """Format signal as full message."""
    if not signal:
        return ""
    
    return f"""
📊 *SIGNAL ALERT*
━━━━━━━━━━━━━━━━━━━━━━

🔹 Symbol: {signal['symbol']}
🔹 Direction: {signal['direction']}
🔹 Regime: {signal['regime']}

📈 Entry: {signal['entry']}
📉 Stop Loss: {signal['sl']}
🎯 TP1: {signal['tp1']}
🎯 TP2: {signal['tp2']}

━━━━━━━━━━━━━━
Confidence: {signal['confidence']:.0%}
Setup Grade: {signal['setup_grade']}
━━━━━━━━━━━━━━

#SMC #TradingBot
"""


# ============================================================================
# MAIN LOOP
# ============================================================================

async def main():
    """Main event loop."""
    config = Config()
    
    print()
    print(f"Symbols: {config.SYMBOLS}")
    print(f"Interval: {config.LOOP_INTERVAL}s")
    print(f"Telegram: {'✓' if config.TOKEN else '✗'}")
    print()
    
    # Cooldown tracking
    last_signals = {}
    
    start_time = time.time()
    iteration = 0
    
    while True:
        try:
            print("-"*40)
            print(f"Iteration {iteration + 1}")
            
            signals_found = 0
            
            for symbol in config.SYMBOLS:
                # Get real market data
                data = get_market_data(symbol)
                
                # Generate signal
                signal = generate_signal(data)
                
                if not signal:
                    continue
                
                # Check cooldown
                last_time = last_signals.get(symbol, 0)
                if time.time() - last_time < config.COOLDOWN:
                    print(f"  {symbol}: Cooldown")
                    continue
                
                # Check quality
                if signal["confidence"] < config.MIN_CONFIDENCE:
                    print(f"  {symbol}: Weak ({signal['confidence']:.0%})")
                    continue
                
                # Record and send
                last_signals[symbol] = time.time()
                signals_found += 1
                
                # Format
                msg = format_signal_full(signal)
                
                # Send
                await send_telegram(msg, config)
                
                print(f"  {signal['symbol']}: {signal['direction']} {signal['confidence']:.0%}")
            
            # Stats
            runtime = (time.time() - start_time) / 60
            print(f"Found: {signals_found} signals")
            print(f"Runtime: {runtime:.1f} min")
            
            # Wait
            iteration += 1
            await asyncio.sleep(config.LOOP_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n✅ Stopped by user")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            await asyncio.sleep(10)


# ============================================================================
# ENTRY
# ============================================================================

if __name__ == "__main__":
    print("Starting...")
    asyncio.run(main())