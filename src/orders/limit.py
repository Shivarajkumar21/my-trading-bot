"""Limit order implementation for Binance Futures."""
from .base import Order
from ..config import logger

class LimitOrder(Order):
    """Limit order implementation."""
    
    def __init__(self, client, symbol, side, quantity, price, **kwargs):
        """Initialize a limit order.
        
        Args:
            client: BinanceFuturesClient instance.
            symbol (str): Trading pair symbol (e.g., 'BTCUSDT').
            side (str): 'BUY' or 'SELL'.
            quantity (float): Order quantity in base asset.
            price (float): Limit price for the order.
            **kwargs: Additional order parameters.
        """
        self.price = float(price)
        super().__init__(client, symbol, side, quantity, **kwargs)
        self.order_type = 'LIMIT'
        self.time_in_force = kwargs.get('timeInForce', 'GTC')  # Good Till Cancel by default
        
        # Validate price
        if self.price <= 0:
            raise ValueError("Price must be greater than 0")
            
        logger.info(f"Initialized {self}")
    
    def place(self):
        """Place a limit order on the exchange.
        
        Returns:
            dict: Order response from the exchange.
        """
        try:
            logger.info(f"Placing {self}")
            
            # Prepare order parameters
            params = {
                'symbol': self.symbol,
                'side': self.side,
                'type': 'LIMIT',
                'timeInForce': self.time_in_force,
                'quantity': self.quantity,
                'price': self.price,
                'newOrderRespType': 'FULL'  # Get full response with all fields
            }
            
            # Add any additional parameters
            params.update(self.params)
            
            # Place the order
            response = self.client.client.futures_create_order(**params)
            
            # Update order status
            self.order_id = response['orderId']
            self.status = response['status']
            
            # If order was filled immediately
            if 'executedQty' in response:
                self.filled_quantity = float(response['executedQty'])
                self.filled_price = float(response['avgPrice']) if 'avgPrice' in response else 0.0
                self.commission = sum(
                    float(fill['commission']) 
                    for fill in response.get('fills', [])
                )
                
                if self.status == 'FILLED':
                    self.filled_at = response['updateTime']
            
            logger.info(f"Order {self.order_id} placed successfully. "
                       f"Status: {self.status}, Filled: {self.filled_quantity}/{self.quantity}")
            
            return response
            
        except Exception as e:
            self.status = 'FAILED'
            logger.error(f"Error placing limit order: {e}")
            raise
    
    def modify(self, quantity=None, price=None):
        """Modify an existing limit order.
        
        Args:
            quantity (float, optional): New quantity. If None, keeps current quantity.
            price (float, optional): New price. If None, keeps current price.
            
        Returns:
            dict: Modification response from the exchange.
        """
        if not self.order_id:
            raise ValueError("Cannot modify an order that hasn't been placed yet")
            
        if quantity is None and price is None:
            raise ValueError("Must specify either quantity or price to modify")
            
        try:
            # Cancel the existing order
            self.cancel()
            
            # Create a new order with updated parameters
            new_quantity = quantity if quantity is not None else self.quantity
            new_price = price if price is not None else self.price
            
            # Update instance variables
            self.quantity = new_quantity
            self.price = new_price
            
            # Place the new order
            return self.place()
            
        except Exception as e:
            logger.error(f"Error modifying order {self.order_id}: {e}")
            raise

    def __str__(self):
        """String representation of the limit order."""
        return (f"{self.order_type} {self.side} {self.quantity} {self.symbol} @ {self.price} "
                f"(Status: {self.status}, ID: {self.order_id or 'N/A'})")
