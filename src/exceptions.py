"""Custom exceptions for the Binance Futures trading bot."""

class OrderError(Exception):
    """Base exception for order-related errors."""
    pass

class ValidationError(OrderError):
    """Raised when input validation fails."""
    pass

class InsufficientFundsError(OrderError):
    """Raised when there are insufficient funds for an order."""
    pass

class OrderQuantityTooSmall(OrderError):
    """Raised when order quantity is below the minimum allowed."""
    pass

class OrderPriceTooSmall(OrderError):
    """Raised when order price is below the minimum allowed."""
    pass
