"""
Execution Module - Order Management.
"""

import asyncio
from dataclasses import dataclass
from typing import Optional
import logging
import ib_insync as ib
from ib_insync.contract import Contract
from ib_insync.order import Order

logger = logging.getLogger(__name__)


@dataclass
class OrderStatus:
    """Order status."""
    order_id: int
    symbol: str
    direction: str
    status: str
    filled: int
    remaining: int
    avg_fill_price: float


class Execution:
    """Execution handler."""
    
    def __init__(self, ib_client, config: dict):
        self.ib = ib_client
        self.config = config
        self._orders = {}
        self._pending = {}
        self._order_id = 0
    
    async def submit_order(
        self,
        symbol: str,
        direction: str,
        quantity: int,
        order_type: str = "MKT"
    ) -> Optional[int]:
        """Submit order to IB."""
        self._order_id += 1
        
        contract, order = self._create_order(symbol, direction, quantity, order_type)
        
        try:
            self.ib.placeOrder(self._order_id, contract, order)
            
            self._orders[self._order_id] = OrderStatus(
                order_id=self._order_id,
                symbol=symbol,
                direction=direction,
                status="Submitted",
                filled=0,
                remaining=quantity,
                avg_fill_price=0.0
            )
            
            logger.info(f"Order {self._order_id}: {direction} {quantity} {symbol}")
            
            return self._order_id
            
        except Exception as e:
            logger.error(f"Order failed: {e}")
            return None
    
    def _create_order(self, symbol: str, direction: str, quantity: int, order_type: str):
        """Create IB order."""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "CASH"
        contract.exchange = "IDEALUSD"
        contract.currency = symbol[3:] if len(symbol) > 3 else "USD"
        
        order = Order()
        order.action = "BUY" if direction == "LONG" else "SELL"
        order.orderType = order_type
        order.totalQuantity = quantity
        
        return contract, order
    
    def on_order_status(self, order_id: int, status: str, filled: int, avg_price: float):
        """Handle order status update."""
        if order_id in self._orders:
            o = self._orders[order_id]
            o.status = status
            o.filled = filled
            o.avg_fill_price = avg_price
            
            logger.info(f"Order {order_id}: {status} {filled}/{o.filled + o.remaining}")
    
    def on_exec_details(self, order_id: int, contract, execution):
        """Handle execution details."""
        logger.debug(f"Exec: {order_id}")
    
    def get_order(self, order_id: int) -> Optional[OrderStatus]:
        """Get order status."""
        return self._orders.get(order_id)
    
    def cancel_order(self, order_id: int) -> bool:
        """Cancel order."""
        try:
            self.ib.cancelOrder(order_id)
            logger.info(f"Cancelled order {order_id}")
            return True
        except Exception as e:
            logger.error(f"Cancel failed: {e}")
            return False