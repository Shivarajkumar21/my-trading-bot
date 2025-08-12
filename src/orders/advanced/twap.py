"""TWAP (Time-Weighted Average Price) order implementation for Binance Futures."""
import time
from datetime import datetime, timedelta
from ...config import logger

class TWAPOrder:
    """TWAP (Time-Weighted Average Price) order implementation.
    
    A TWAP order splits a large order into smaller chunks and executes them over a specified
    time period to minimize market impact. This is particularly useful for large orders.
    """
    
    def __init__(self, client, symbol, side, total_quantity, 
                 duration_minutes=60, chunks=12, price_limit=None, **kwargs):
        """Initialize a TWAP order.
        
        Args:
            client: BinanceFuturesClient instance.
            symbol (str): Trading pair symbol (e.g., 'BTCUSDT').
            side (str): 'BUY' or 'SELL'.
            total_quantity (float): Total order quantity in base asset.
            duration_minutes (int): Total duration in minutes over which to execute the order.
            chunks (int): Number of smaller orders to split the total quantity into.
            price_limit (float, optional): Maximum price for BUY or minimum price for SELL.
            **kwargs: Additional order parameters.
        """
        self.client = client
        self.symbol = symbol.upper()
        self.side = side.upper()
        self.total_quantity = float(total_quantity)
        self.duration_minutes = int(duration_minutes)
        self.chunks = int(chunks)
        self.price_limit = float(price_limit) if price_limit is not None else None
        self.params = kwargs
        
        # Calculate chunk size and interval
        self.chunk_size = self.total_quantity / self.chunks
        self.interval_seconds = (self.duration_minutes * 60) / self.chunks
        
        # Order tracking
        self.status = 'INITIALIZED'
        self.created_at = datetime.utcnow()
        self.orders = []
        self.completed_orders = 0
        self.filled_quantity = 0.0
        self.average_price = 0.0
        
        # Validate inputs
        self._validate_inputs()
        
        logger.info(f"Initialized {self}")
    
    def _validate_inputs(self):
        """Validate order inputs."""
        if self.side not in ['BUY', 'SELL']:
            raise ValueError("Side must be either 'BUY' or 'SELL'")
            
        if self.total_quantity <= 0:
            raise ValueError("Total quantity must be greater than 0")
            
        if self.duration_minutes <= 0:
            raise ValueError("Duration must be greater than 0")
            
        if self.chunks <= 0:
            raise ValueError("Number of chunks must be greater than 0")
            
        if self.chunks > 100:
            raise ValueError("Maximum number of chunks is 100")
            
        if not self.client.validate_symbol(self.symbol):
            raise ValueError(f"Invalid or inactive trading symbol: {self.symbol}")
            
        if self.price_limit is not None and self.price_limit <= 0:
            raise ValueError("Price limit must be greater than 0")
    
    def _place_chunk(self, chunk_number):
        """Place a single chunk order.
        
        Args:
            chunk_number (int): The chunk number being placed (1-based index).
            
        Returns:
            dict: Order response from the exchange.
        """
        try:
            # Calculate remaining quantity for this chunk
            remaining_quantity = self.total_quantity - self.filled_quantity
            chunk_qty = min(self.chunk_size, remaining_quantity)
            
            if chunk_qty <= 0:
                logger.info("No more quantity to execute")
                return None
            
            # Get current price for limit orders if needed
            current_price = self.client.get_price(self.symbol)
            
            # Check price limit if set
            if self.price_limit is not None:
                if (self.side == 'BUY' and current_price > self.price_limit) or \
                   (self.side == 'SELL' and current_price < self.price_limit):
                    logger.warning(
                        f"Current price {current_price} is outside the limit price {self.price_limit}. "
                        f"Skipping chunk {chunk_number}."
                    )
                    return None
            
            # Place a market order for simplicity
            # In a real-world scenario, you might want to use limit orders with a small offset
            order_params = {
                'symbol': self.symbol,
                'side': self.side,
                'type': 'MARKET',
                'quantity': chunk_qty,
                'newOrderRespType': 'FULL'
            }
            
            # Add any additional parameters
            order_params.update(self.params)
            
            logger.info(f"Placing chunk {chunk_number}/{self.chunks}: {self.side} {chunk_qty} {self.symbol}")
            
            # Place the order
            response = self.client.client.futures_create_order(**order_params)
            
            # Update order tracking
            filled_qty = float(response.get('executedQty', 0))
            avg_price = float(response.get('avgPrice', 0))
            
            self.orders.append({
                'order_id': response['orderId'],
                'quantity': filled_qty,
                'price': avg_price,
                'timestamp': datetime.utcnow(),
                'response': response
            })
            
            # Update filled quantity and average price
            if filled_qty > 0:
                old_total = self.filled_quantity * self.average_price if self.filled_quantity > 0 else 0
                self.filled_quantity += filled_qty
                self.average_price = (old_total + (filled_qty * avg_price)) / self.filled_quantity
                self.completed_orders += 1
                
                logger.info(
                    f"Chunk {chunk_number} filled: {filled_qty} {self.symbol} @ {avg_price} "
                    f"(Total filled: {self.filled_quantity}/{self.total_quantity})"
                )
            
            return response
            
        except Exception as e:
            logger.error(f"Error placing chunk {chunk_number}: {e}")
            raise
    
    def execute(self):
        """Execute the TWAP order by placing chunks at regular intervals.
        
        Returns:
            dict: Summary of the TWAP execution.
        """
        if self.status != 'INITIALIZED':
            raise ValueError("TWAP order has already been executed")
        
        self.status = 'EXECUTING'
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(minutes=self.duration_minutes)
        
        logger.info(
            f"Starting TWAP execution: {self.total_quantity} {self.symbol} {self.side} "
            f"over {self.duration_minutes} minutes in {self.chunks} chunks"
        )
        
        try:
            # Place the first chunk immediately
            self._place_chunk(1)
            
            # Place remaining chunks at regular intervals
            for i in range(2, self.chunks + 1):
                # Calculate sleep time, ensuring we don't exceed the end time
                current_time = datetime.utcnow()
                time_elapsed = (current_time - start_time).total_seconds()
                expected_time_elapsed = (i - 1) * self.interval_seconds
                sleep_time = max(0, expected_time_elapsed - time_elapsed)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
                # Place the next chunk
                self._place_chunk(i)
                
                # Check if we've filled the total quantity
                if self.filled_quantity >= self.total_quantity:
                    logger.info("Total quantity filled. Stopping TWAP execution.")
                    break
            
            # Update status
            if self.filled_quantity >= self.total_quantity * 0.99:  # Allow for small rounding errors
                self.status = 'COMPLETED'
                logger.info("TWAP execution completed successfully")
            else:
                self.status = 'PARTIALLY_FILLED'
                logger.warning(
                    f"TWAP execution partially completed: "
                    f"{self.filled_quantity}/{self.total_quantity} filled"
                )
            
            return {
                'status': self.status,
                'total_quantity': self.total_quantity,
                'filled_quantity': self.filled_quantity,
                'average_price': self.average_price,
                'orders_placed': len(self.orders),
                'start_time': start_time,
                'end_time': datetime.utcnow()
            }
            
        except Exception as e:
            self.status = 'FAILED'
            logger.error(f"TWAP execution failed: {e}")
            raise
        finally:
            # Ensure we log the final status
            logger.info(
                f"TWAP execution finished with status: {self.status}. "
                f"Filled: {self.filled_quantity}/{self.total_quantity} "
                f"@ avg price: {self.average_price}"
            )
    
    def cancel(self):
        """Cancel any remaining chunks of the TWAP order.
        
        Returns:
            list: List of cancellation responses.
        """
        if self.status not in ['EXECUTING', 'PARTIALLY_FILLED']:
            logger.warning(f"Cannot cancel TWAP order in status: {self.status}")
            return []
        
        logger.info(f"Canceling remaining chunks of TWAP order")
        self.status = 'CANCELED'
        
        # In a real implementation, you might want to track open orders and cancel them
        # For market orders, they're typically filled immediately, so nothing to cancel
        return []
    
    def get_status(self):
        """Get the current status of the TWAP order.
        
        Returns:
            dict: Current status information.
        """
        return {
            'status': self.status,
            'symbol': self.symbol,
            'side': self.side,
            'total_quantity': self.total_quantity,
            'filled_quantity': self.filled_quantity,
            'average_price': self.average_price,
            'chunks_placed': len(self.orders),
            'chunks_completed': self.completed_orders,
            'created_at': self.created_at
        }
    
    def __str__(self):
        """String representation of the TWAP order."""
        return (f"TWAP {self.side} {self.total_quantity} {self.symbol} "
                f"over {self.duration_minutes}min in {self.chunks} chunks "
                f"(Status: {self.status}, Filled: {self.filled_quantity}/{self.total_quantity})")
