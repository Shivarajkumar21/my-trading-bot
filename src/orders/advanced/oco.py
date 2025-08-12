"""OCO (One-Cancels-Other) order implementation for Binance Futures."""
import time
from datetime import datetime
from ...config import logger

class OCOOrder:
    """OCO (One-Cancels-Other) order implementation.
    
    An OCO order allows you to place two linked orders where if one order is executed,
    the other order is automatically canceled. This is useful for implementing take-profit
    and stop-loss orders together.
    """
    
    def __init__(self, client, symbol, side, quantity, 
                 limit_price, stop_price, stop_limit_price, **kwargs):
        """Initialize an OCO order.
        
        Args:
            client: BinanceFuturesClient instance.
            symbol (str): Trading pair symbol (e.g., 'BTCUSDT').
            side (str): 'BUY' or 'SELL'.
            quantity (float): Order quantity in base asset.
            limit_price (float): Price for the limit order (take-profit).
            stop_price (float): Price at which the stop order is triggered.
            stop_limit_price (float): Price for the stop-limit order (stop-loss).
            **kwargs: Additional order parameters.
        """
        self.client = client
        self.symbol = symbol.upper()
        self.side = side.upper()
        self.quantity = float(quantity)
        self.limit_price = float(limit_price)
        self.stop_price = float(stop_price)
        self.stop_limit_price = float(stop_limit_price)
        self.params = kwargs
        
        self.order_id = None
        self.status = 'INITIALIZED'
        self.created_at = datetime.utcnow()
        self.orders = {}  # To store the individual orders
        
        # Validate inputs
        self._validate_inputs()
        
        logger.info(f"Initialized {self}")
    
    def _validate_inputs(self):
        """Validate order inputs."""
        if self.side not in ['BUY', 'SELL']:
            raise ValueError("Side must be either 'BUY' or 'SELL'")
            
        if self.quantity <= 0:
            raise ValueError("Quantity must be greater than 0")
            
        if self.limit_price <= 0 or self.stop_price <= 0 or self.stop_limit_price <= 0:
            raise ValueError("All prices must be greater than 0")
            
        if not self.client.validate_symbol(self.symbol):
            raise ValueError(f"Invalid or inactive trading symbol: {self.symbol}")
            
        # For BUY orders, limit price should be below stop price
        # For SELL orders, limit price should be above stop price
        if (self.side == 'BUY' and self.limit_price >= self.stop_price) or \
           (self.side == 'SELL' and self.limit_price <= self.stop_price):
            raise ValueError(
                f"For {self.side} orders, limit price ({self.limit_price}) must be "
                f"{'below' if self.side == 'BUY' else 'above'} stop price ({self.stop_price})"
            )
    
    def place(self):
        """Place an OCO order on the exchange.
        
        Note: Binance Futures doesn't support native OCO orders like Spot does,
        so we implement it by placing two separate orders and managing them.
        
        Returns:
            dict: Order response from the exchange.
        """
        try:
            logger.info(f"Placing {self}")
            
            # Get current price to determine order types
            current_price = self.client.get_price(self.symbol)
            
            # Place the limit order (take-profit)
            limit_order = {
                'symbol': self.symbol,
                'side': self.side,
                'type': 'LIMIT',
                'timeInForce': 'GTC',
                'quantity': self.quantity,
                'price': self.limit_price,
                'newOrderRespType': 'FULL'
            }
            
            # Place the stop-limit order (stop-loss)
            stop_order = {
                'symbol': self.symbol,
                'side': 'SELL' if self.side == 'BUY' else 'BUY',  # Opposite side for stop-loss
                'type': 'STOP_LOSS_LIMIT',
                'timeInForce': 'GTC',
                'quantity': self.quantity,
                'price': self.stop_limit_price,
                'stopPrice': self.stop_price,
                'newOrderRespType': 'FULL'
            }
            
            # Add any additional parameters
            limit_order.update(self.params)
            stop_order.update(self.params)
            
            # Place the limit order (take-profit)
            limit_response = self.client.client.futures_create_order(**limit_order)
            limit_order_id = limit_response['orderId']
            
            # Small delay to ensure orders are processed in order
            time.sleep(0.5)
            
            # Place the stop-limit order (stop-loss)
            stop_response = self.client.client.futures_create_order(**stop_order)
            stop_order_id = stop_response['orderId']
            
            # Store order information
            self.orders = {
                'limit_order': {'id': limit_order_id, 'response': limit_response},
                'stop_order': {'id': stop_order_id, 'response': stop_response}
            }
            
            self.status = 'PLACED'
            logger.info(f"OCO order placed successfully. "
                       f"Limit Order ID: {limit_order_id}, Stop Order ID: {stop_order_id}")
            
            return {
                'status': 'success',
                'limit_order': limit_response,
                'stop_order': stop_response
            }
            
        except Exception as e:
            self.status = 'FAILED'
            logger.error(f"Error placing OCO order: {e}")
            
            # Cancel any orders that might have been placed
            self.cancel()
            raise
    
    def cancel(self):
        """Cancel all orders in the OCO group.
        
        Returns:
            dict: Cancellation responses.
        """
        results = {}
        
        try:
            # Cancel limit order if it exists
            if 'limit_order' in self.orders and self.orders['limit_order']['id']:
                result = self.client.client.futures_cancel_order(
                    symbol=self.symbol,
                    orderId=self.orders['limit_order']['id']
                )
                results['limit_order'] = result
                logger.info(f"Canceled limit order {self.orders['limit_order']['id']}")
            
            # Cancel stop order if it exists
            if 'stop_order' in self.orders and self.orders['stop_order']['id']:
                result = self.client.client.futures_cancel_order(
                    symbol=self.symbol,
                    orderId=self.orders['stop_order']['id']
                )
                results['stop_order'] = result
                logger.info(f"Canceled stop order {self.orders['stop_order']['id']}")
            
            self.status = 'CANCELED'
            return results
            
        except Exception as e:
            logger.error(f"Error canceling OCO orders: {e}")
            raise
    
    def get_status(self):
        """Get the status of all orders in the OCO group.
        
        Returns:
            dict: Status of all orders.
        """
        results = {}
        
        try:
            if 'limit_order' in self.orders and self.orders['limit_order']['id']:
                limit_status = self.client.client.futures_get_order(
                    symbol=self.symbol,
                    orderId=self.orders['limit_order']['id']
                )
                results['limit_order'] = limit_status
                
                # Update overall status if any order is filled
                if limit_status.get('status') == 'FILLED':
                    self.status = 'LIMIT_FILLED'
                    
                    # Cancel the stop order if limit is filled
                    if 'stop_order' in self.orders and self.orders['stop_order']['id']:
                        try:
                            self.client.client.futures_cancel_order(
                                symbol=self.symbol,
                                orderId=self.orders['stop_order']['id']
                            )
                            logger.info(f"Canceled stop order {self.orders['stop_order']['id']} "
                                       f"as limit order was filled")
                        except Exception as e:
                            logger.warning(f"Error canceling stop order: {e}")
            
            if 'stop_order' in self.orders and self.orders['stop_order']['id']:
                stop_status = self.client.client.futures_get_order(
                    symbol=self.symbol,
                    orderId=self.orders['stop_order']['id']
                )
                results['stop_order'] = stop_status
                
                # Update overall status if stop order is filled
                if stop_status.get('status') == 'FILLED':
                    self.status = 'STOP_FILLED'
                    
                    # Cancel the limit order if stop is filled
                    if 'limit_order' in self.orders and self.orders['limit_order']['id']:
                        try:
                            self.client.client.futures_cancel_order(
                                symbol=self.symbol,
                                orderId=self.orders['limit_order']['id']
                            )
                            logger.info(f"Canceled limit order {self.orders['limit_order']['id']} "
                                       f"as stop order was triggered")
                        except Exception as e:
                            logger.warning(f"Error canceling limit order: {e}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting OCO order status: {e}")
            raise

    def __str__(self):
        """String representation of the OCO order."""
        return (f"OCO {self.side} {self.quantity} {self.symbol} "
                f"Limit: {self.limit_price}, Stop: {self.stop_price}@{self.stop_limit_price} "
                f"(Status: {self.status})")
