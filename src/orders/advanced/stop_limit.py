"""Stop-Limit order implementation for Binance Futures."""
from ..limit import LimitOrder
from ...config import logger

class StopLimitOrder(LimitOrder):
    """Stop-Limit order implementation.
    
    A Stop-Limit order is an order to buy or sell an asset when its price reaches a specified
    stop price. Once the stop price is reached, a limit order is placed at the specified limit price.
    """
    
    def __init__(self, client, symbol, side, quantity, stop_price, limit_price, **kwargs):
        """Initialize a stop-limit order.
        
        Args:
            client: BinanceFuturesClient instance.
            symbol (str): Trading pair symbol (e.g., 'BTCUSDT').
            side (str): 'BUY' or 'SELL'.
            quantity (float): Order quantity in base asset.
            stop_price (float): Price at which the stop order is triggered.
            limit_price (float): Price at which the limit order will be placed.
            **kwargs: Additional order parameters.
        """
        # Initialize with limit_price as the price for the limit order
        super().__init__(client, symbol, side, quantity, limit_price, **kwargs)
        
        self.order_type = 'STOP_LOSS_LIMIT'  # Binance-specific order type
        self.stop_price = float(stop_price)
        
        # Validate stop price
        if self.stop_price <= 0:
            raise ValueError("Stop price must be greater than 0")
            
        # For BUY orders, stop price should be above the current price
        # For SELL orders, stop price should be below the current price
        current_price = self.client.get_price(symbol)
        if (side == 'BUY' and self.stop_price <= current_price) or \
           (side == 'SELL' and self.stop_price >= current_price):
            logger.warning(
                f"For {side} orders, stop price ({self.stop_price}) should be "
                f"{'above' if side == 'BUY' else 'below'} current price ({current_price})"
            )
        
        logger.info(f"Initialized {self}")
    
    def place(self):
        """Place a stop-limit order on the exchange.
        
        Returns:
            dict: Order response from the exchange.
        """
        try:
            logger.info(f"Placing {self}")
            
            # Prepare order parameters
            params = {
                'symbol': self.symbol,
                'side': self.side,
                'type': self.order_type,
                'timeInForce': self.time_in_force,
                'quantity': self.quantity,
                'price': self.price,  # This is the limit price
                'stopPrice': self.stop_price,
                'newOrderRespType': 'FULL'
            }
            
            # Add any additional parameters
            params.update(self.params)
            
            # Place the order
            response = self.client.client.futures_create_order(**params)
            
            # Update order status
            self.order_id = response['orderId']
            self.status = response['status']
            
            # If order was filled immediately (should be rare for stop-limit)
            if 'executedQty' in response:
                self.filled_quantity = float(response['executedQty'])
                self.filled_price = float(response['avgPrice']) if 'avgPrice' in response else 0.0
                self.commission = sum(
                    float(fill['commission']) 
                    for fill in response.get('fills', [])
                )
                
                if self.status == 'FILLED':
                    self.filled_at = response['updateTime']
            
            logger.info(f"Stop-limit order {self.order_id} placed successfully. "
                       f"Status: {self.status}")
            
            return response
            
        except Exception as e:
            self.status = 'FAILED'
            logger.error(f"Error placing stop-limit order: {e}")
            raise
    
    def modify(self, quantity=None, limit_price=None, stop_price=None):
        """Modify an existing stop-limit order.
        
        Args:
            quantity (float, optional): New quantity. If None, keeps current quantity.
            limit_price (float, optional): New limit price. If None, keeps current limit price.
            stop_price (float, optional): New stop price. If None, keeps current stop price.
            
        Returns:
            dict: Modification response from the exchange.
        """
        if not self.order_id:
            raise ValueError("Cannot modify an order that hasn't been placed yet")
            
        if quantity is None and limit_price is None and stop_price is None:
            raise ValueError("Must specify at least one parameter to modify")
            
        try:
            # Cancel the existing order
            self.cancel()
            
            # Update instance variables
            if quantity is not None:
                self.quantity = quantity
            if limit_price is not None:
                self.price = limit_price
            if stop_price is not None:
                self.stop_price = stop_price
            
            # Place the new order
            return self.place()
            
        except Exception as e:
            logger.error(f"Error modifying stop-limit order {self.order_id}: {e}")
            raise

    def __str__(self):
        """String representation of the stop-limit order."""
        return (f"{self.order_type} {self.side} {self.quantity} {self.symbol} "
                f"Stop: {self.stop_price}, Limit: {self.price} "
                f"(Status: {self.status}, ID: {self.order_id or 'N/A'})")
