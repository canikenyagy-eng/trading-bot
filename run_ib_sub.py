#!/usr/bin/env python3
"""
IB Runner - Fixed for Python 3.14 using subprocess
"""

import subprocess
import sys
import os

# Create a temp script that will be run by ib_insync's event loop
SCRIPT = '''
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from ib_insync import IB, Contract

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger()

async def subscribe(ib, symbol):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "CASH"
    contract.exchange = "IDEALUSD"
    contract.currency = "USD"
    
    ticker = ib.reqMktData(1, contract, "", True, False)
    
    def on_tick(ticker):
        if ticker.last:
            logger.info(f"{symbol}: bid={ticker.bid}, ask={ticker.ask}, last={ticker.last}")
    
    ticker.updateEvent += on_tick
    return ticker

async def main():
    try:
        ib = IB()
        ib.connect("127.0.0.1", 7497, clientId=1)
        logger.info("Connected to IB port 7497")
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        return
    
    symbols = ["EURUSD", "GBPUSD", "USDJPY"]
    for symbol in symbols:
        await subscribe(ib, symbol)
    
    logger.info(f"Subscribed to {len(symbols)} symbols")
    logger.info("Press Ctrl+C to stop")
    
    ib.run()

asyncio.run(main())
'''

def main():
    """Run in subprocess to avoid event loop issues."""
    print("Starting IB Runner...")
    print("Make sure IB Gateway/TWS is running on port 7497")
    print()
    
    # Run the script
    result = subprocess.run(
        [sys.executable, "-c", SCRIPT],
        cwd=os.getcwd(),
        env={**os.environ, "PYTHONPATH": os.getcwd()}
    )


if __name__ == "__main__":
    main()