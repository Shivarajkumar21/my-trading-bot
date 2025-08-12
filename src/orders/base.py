"""Base order class for Binance Futures trading with validation and error handling."""
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from typing import Dict, Optional, Tuple

from ..config import logger
from ..exceptions import (
    OrderError, ValidationError, InsufficientFundsError,
    OrderQuantityTooSmall, OrderPriceTooSmall
)

class Order(ABC):
    """Abstract base class for all order types with validation and error handling.
    
    This class provides the foundation for all order types with the following features:
    - Input validation for all order parameters
    - Consistent error handling and logging
    - Order status tracking
    - Common order operations (cancel, check status)
    """
    
    # Class constants
    VALID_SIDES = {'BUY', 'SELL'}
    VALID_STATUSES = {
        'INITIALIZED', 'NEW', 'PARTIALLY_FILLED', 'FILLED',
        'CANCELED', 'PENDING_CANCEL', 'REJECTED', 'EXPIRED'
    }
    
    def __init__(self, client, symbol: str, side: str, quantity: float, **kwargs):
        """Initialize the base order with validation.
        
        Args:
            client: BinanceFuturesClient instance.
            symbol: Trading pair symbol (e.g., 'BTCUSDT').
            side: 'BUY' or 'SELL'.
            quantity: Order quantity in base asset.
            **kwargs: Additional order parameters.
            
        Raises:
            ValidationError: If input validation fails.
            OrderError: For order-specific validation errors.
        """
        # Basic type validation
        if not hasattr(client, 'client'):
            raise ValidationError("Invalid client: Must be a BinanceFuturesClient instance")
            
        if not isinstance(symbol, str):
            raise ValidationError("Symbol must be a string")
            
        # Store parameters with validation
        self.client = client
        self.symbol = symbol.upper()
        self.original_quantity = self._validate_quantity(quantity)
        self.side = self._validate_side(side)
        self.params = {k: v for k, v in kwargs.items() if v is not None}
        
        # Initialize order state
        self.order_id: Optional[str] = None
        self.status: str = 'INITIALIZED'
        self.created_at: datetime = datetime.utcnow()
        self.updated_at: datetime = self.created_at
        self.filled_at: Optional[datetime] = None
        self.filled_quantity: float = 0.0
        self.avg_fill_price: float = 0.0
        self.commission: float = 0.0
        
        # Additional validations that might need API calls
        self._post_init_validation()
        
        logger.info(f"Initialized {self.side} {self.__class__.__name__} order: {self.original_quantity} {self.symbol}")
    
    def _validate_quantity(self, quantity) -> float:
        """Validate and convert order quantity.
        
        Args:
            quantity: The quantity to validate and convert.
            
        Returns:
            float: Validated quantity with proper precision.
            
        Raises:
            ValidationError: If quantity is invalid.
            OrderQuantityTooSmall: If quantity is below minimum allowed.
        """
        try:
            # Convert to float
            qty = float(quantity)
            
            # Basic validation
            if qty <= 0:
                raise ValidationError(f"Quantity must be greater than 0, got {quantity}")
                
            # Get symbol info for precision and lot size
            symbol_info = self.client.get_symbol_info(self.symbol)
            if not symbol_info:
                logger.warning(f"Could not get symbol info for {self.symbol}, skipping quantity validation")
                return qty
                
            # Get lot size filter if available
            lot_size = next(
                (f for f in symbol_info.get('filters', []) if f.get('filterType') == 'LOT_SIZE'),
                None
            )
            
            if lot_size:
                min_qty = float(lot_size.get('minQty', 0))
                max_qty = float(lot_size.get('maxQty', float('inf')))
                step_size = float(lot_size.get('stepSize', 0))
                
                if qty < min_qty:
                    raise OrderQuantityTooSmall(
                        f"Quantity {qty} is below minimum {min_qty} for {self.symbol}"
                    )
                    
                if qty > max_qty:
                    raise ValidationError(
                        f"Quantity {qty} exceeds maximum {max_qty} for {self.symbol}"
                    )
                
                # Round to step size if needed
                if step_size > 0:
                    qty = (qty // step_size) * step_size
            
            return qty
            
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Invalid quantity: {quantity}") from e
    
    def _validate_side(self, side: str) -> str:
        """Validate order side."""
        side_upper = str(side).upper()
        if side_upper not in self.VALID_SIDES:
            raise ValidationError(
                f"Invalid side: {side}. Must be one of {', '.join(self.VALID_SIDES)}"
            )
        return side_upper
    
    def _post_init_validation(self):
        """Perform validation that requires API calls or additional context."""
        # Validate symbol
        if not self.client.validate_symbol(self.symbol):
            raise ValidationError(f"Invalid or inactive trading symbol: {self.symbol}")
        
        # Additional validations can be added here
        # For example, checking account balance, position limits, etc.
    
    @abstractmethod
    def place(self) -> dict:
        """Place the order on the exchange.
        
        Returns:
            dict: Order response from the exchange.
            
        Raises:
            OrderError: If the order cannot be placed.
            ValidationError: If order validation fails.
            InsufficientFundsError: If there are insufficient funds for the order.
            OrderQuantityTooSmall: If the order quantity is below the minimum.
            OrderPriceTooSmall: If the order price is below the minimum.
        """
        pass
    
    def cancel(self, order_id: str = None) -> dict:
        """Cancel an active order.
        
        Args:
            order_id: Order ID to cancel. If None, uses self.order_id.
            
        Returns:
            dict: Cancellation response from the exchange.
            
        Raises:
            OrderError: If cancellation fails.
            ValidationError: If order_id is invalid.
        """
        order_id = order_id or self.order_id
        if not order_id:
            raise ValidationError("No order ID provided to cancel")
            
        if not isinstance(order_id, str):
            raise ValidationError(f"Order ID must be a string, got {type(order_id)}")
            
        try:
            result = self.client.client.futures_cancel_order(
                symbol=self.symbol,
                orderId=order_id
            )
            
            # Update order status
            self.status = 'CANCELED'
            self.updated_at = datetime.utcnow()
            
            logger.info(f"Order {order_id} canceled successfully")
            return result
            
        except Exception as e:
            error_msg = f"Error canceling order {order_id}: {e}"
            logger.error(error_msg)
            raise OrderError(error_msg) from e
    
    def get_status(self, order_id: str = None) -> dict:
        """Get the status of an order.
        
        Args:
            order_id: Order ID to check. If None, uses self.order_id.
            
        Returns:
            dict: Order status information.
            
        Raises:
            OrderError: If status check fails.
            ValidationError: If order_id is invalid.
        """
        order_id = order_id or self.order_id
        if not order_id:
            raise ValidationError("No order ID provided to check status")
            
        if not isinstance(order_id, str):
            raise ValidationError(f"Order ID must be a string, got {type(order_id)}")
            
        try:
            status = self.client.client.futures_get_order(
                symbol=self.symbol,
                orderId=order_id
            )
            
            # Update order state from status
            self._update_from_status(status)
            
            return status
            
        except Exception as e:
            error_msg = f"Error getting status for order {order_id}: {e}"
            logger.error(error_msg)
            raise OrderError(error_msg) from e
    
    def _update_from_status(self, status: dict) -> None:
        """Update order state from status dictionary."""
        if not status or 'status' not in status:
            return
            
        self.status = status['status']
        self.updated_at = datetime.utcnow()
        
        # Update filled quantity and price if available
        if 'executedQty' in status:
            self.filled_quantity = float(status['executedQty'])
            
        if 'avgPrice' in status and status['avgPrice']:
            self.avg_fill_price = float(status['avgPrice'])
            
        # Update order ID if not set
        if not self.order_id and 'orderId' in status:
            self.order_id = str(status['orderId'])
            
        # Update filled timestamp if order is filled
        if self.status == 'FILLED' and not self.filled_at:
            self.filled_at = datetime.utcnow()
    
    def __str__(self):
        """String representation of the order."""
        return (f"{self.__class__.__name__} {self.side} {self.quantity} {self.symbol} "
                f"(Status: {self.status}, ID: {self.order_id or 'N/A'})")
