"""
Simple IB Runner - Fix for Python 3.14 event loop issues.
"""

import asyncio
import json
import logging
from logging.handlers import RotatingFileHandler
from ib_insync import IB, Contract, Order

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger()


async def connect_ib(port: int = 7497) -> IB:
    """Connect to IB."""
    ib = IB()
    ib.connect('127.0.0.1', port, clientId=1)
    logger.info(f"Connected to IB port {port}")
    return ib


async def subscribe(ib: IB, symbol: str):
    """Subscribe to market data."""
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
    ib = await connect_ib(7497)
    
    symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
    tickers = []
    
    for symbol in symbols:
        ticker = await subscribe(ib, symbol)
        tickers.append(ticker)
    
    logger.info(f"Subscribed to {len(tickers)} symbols")
    logger.info("Press Ctrl+C to stop")
    
    ib.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped")
    except Exception as e:
        logger.error(f"Error: {e}")