#!/usr/bin/env python3
"""
IB Runner - Fixed for Python 3.14 event loop.
Must run as: python3 -c "import asyncio; asyncio.run(main())"
"""

import asyncio
import logging
from logging.handlers import RotatingFileHandler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger()


async def subscribe(ib, symbol: str):
    """Subscribe to market data."""
    from ib_insync import Contract
    
    contract = Contract()
    contract.symbol = symbol
    contract.secType = 'CASH'
    contract.exchange = 'IDEALUSD'
    contract.currency = 'USD'
    
    ticker = ib.reqMktData(1, contract, '', True, False)
    
    def on_tick(ticker):
        if ticker.last:
            logger.info(f"{symbol}: bid={ticker.bid}, ask={ticker.ask}, last={ticker.last}")
    
    ticker.updateEvent += on_tick
    
    return ticker


async def main():
    """Main async function."""
    from ib_insync import IB
    
    try:
        ib = IB()
        ib.connect('127.0.0.1', 7497, clientId=1)
        logger.info("Connected to IB port 7497")
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        return
    
    symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
    tickers = []
    
    for symbol in symbols:
        ticker = await subscribe(ib, symbol)
        tickers.append(ticker)
    
    logger.info(f"Subscribed to {len(tickers)} symbols")
    logger.info("Press Ctrl+C to stop")
    
    # Run IB loop
    ib.run()


if __name__ == "__main__":
    # This is the KEY - use asyncio.run() or run with -c
    try:
        # Python 3.7+
        import asyncio
        asyncio.run(main())
    except TypeError:
        # Older Python - use.run_until_complete
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(main())
        finally:
            loop.close()