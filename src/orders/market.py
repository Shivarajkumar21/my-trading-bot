"""Market order implementation for Binance Futures with comprehensive validation.

This module provides the MarketOrder class that implements market orders with:
- Input validation for all parameters
- Proper error handling and logging
- Support for different time-in-force options
- Position sizing and leverage management
"""
from typing import Dict, Optional, Union
from datetime import datetime

from ..config import logger
from ..exceptions import (
    OrderError, ValidationError, InsufficientFundsError,
    OrderQuantityTooSmall
)
from .base import Order

class MarketOrder(Order):
    """Market order for immediate execution at the best available price.
    
    A market order is an order to buy or sell a security at the best available price.
    Market orders are typically executed immediately and are therefore used when certainty 
    of execution is a priority over the price of execution.
    
    Note: Market orders are subject to slippage, which means the execution price may differ
    from the expected price, especially in volatile markets or with large order sizes.
    """
    
    # Default time in force for market orders
    DEFAULT_TIME_IN_FORCE = 'GTC'  # Good Till Canceled
    
    def __init__(self, client, symbol: str, side: str, quantity: float, **kwargs):
        """Initialize a market order with validation.
        
        Args:
            client: BinanceFuturesClient instance.
            symbol: Trading pair symbol (e.g., 'BTCUSDT').
            side: 'BUY' or 'SELL'.
            quantity: Order quantity in base asset.
            **kwargs: Additional order parameters including:
                - reduce_only (bool, optional): If True, the order will only reduce a position.
                - time_in_force (str, optional): Time in force, default 'GTC'.
                - close_position (bool, optional): If True, closes the entire position.
                - position_side (str, optional): 'BOTH', 'LONG', or 'SHORT'.
                - new_client_order_id (str, optional): A unique ID for the order.
                
        Raises:
            ValidationError: If input validation fails.
            OrderError: For order-specific validation errors.
        """
        # Initialize base order
        super().__init__(client, symbol, side, quantity, **kwargs)
        
        # Set order type
        self.order_type = 'MARKET'
        
        # Set default time in force if not provided
        if 'timeInForce' not in self.params:
            self.params['timeInForce'] = self.DEFAULT_TIME_IN_FORCE
            
        # Set reduce_only flag if provided
        if 'reduce_only' in self.params:
            self.params['reduceOnly'] = 'true' if self.params.pop('reduce_only') else 'false'
            
        # Set close position flag if provided
        if 'close_position' in self.params and self.params['close_position']:
            self.params['closePosition'] = 'true'
            # Remove quantity if closing entire position
            if 'quantity' in self.params:
                del self.params['quantity']
        
        # Log order initialization
        logger.debug(
            f"Initialized {self.side} {self.order_type} order for "
            f"{self.original_quantity} {self.symbol} with params: {self.params}"
        )
    
    def place(self) -> dict:
        """Place a market order on the exchange with comprehensive validation.
        
        Returns:
            dict: Order response from the exchange with order details.
            
        Raises:
            OrderError: If the order cannot be placed.
            ValidationError: If order validation fails.
            InsufficientFundsError: If there are insufficient funds for the order.
            OrderQuantityTooSmall: If the order quantity is below the minimum.
            
        Example:
            >>> client = BinanceFuturesClient()
            >>> order = MarketOrder(client, 'BTCUSDT', 'BUY', 0.001)
            >>> response = order.place()
            >>> print(response)
        """
        try:
            # Prepare order parameters
            order_params = {
                'symbol': self.symbol,
                'side': self.side,
                'type': self.order_type,
                'quantity': self.original_quantity,
                **self.params
            }
            
            # Log order attempt
            logger.info(
                f"Placing {self.side} {self.order_type} order for "
                f"{self.original_quantity} {self.symbol} with params: {self.params}"
            )
            
            # Additional validation before placing the order
            self._pre_place_validation()
            
            # Place the order
            try:
                response = self.client.client.futures_create_order(**order_params)
            except Exception as e:
                error_msg = str(e).lower()
                
                # Handle common API errors
                if 'insufficient balance' in error_msg:
                    raise InsufficientFundsError("Insufficient balance for this order") from e
                elif 'quantity less than or equal to zero' in error_msg:
                    raise OrderQuantityTooSmall("Order quantity must be greater than zero") from e
                elif 'min notional' in error_msg:
                    raise OrderError(f"Order value below minimum notional: {e}") from e
                else:
                    # Re-raise for other errors
                    raise OrderError(f"Failed to place market order: {e}") from e
            
            # Update order details from response
            self._update_from_response(response)
            
            # Log successful placement
            logger.info(
                f"Market order {self.order_id} placed successfully. "
                f"Status: {self.status}, Filled: {self.filled_quantity} @ {self.avg_fill_price}"
            )
            
            return response
            
        except Exception as e:
            error_msg = f"Error placing market order for {self.symbol}: {e}"
            logger.error(error_msg, exc_info=True)
            
            # Update status if we have partial order info
            self.status = 'ERROR'
            self.updated_at = datetime.utcnow()
            
            # Re-raise with appropriate exception type
            if not isinstance(e, (OrderError, ValidationError, InsufficientFundsError)):
                raise OrderError(error_msg) from e
            raise

    def __str__(self):
        """String representation of the market order."""
        return (f"{self.order_type} {self.side} {self.quantity} {self.symbol} "
                f"(Status: {self.status}, ID: {self.order_id or 'N/A'})")
