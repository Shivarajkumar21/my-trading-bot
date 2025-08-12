"""Grid order implementation for Binance Futures."""
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class GridOrder:
    """Grid trading strategy implementation."""
    
    def __init__(self, client, symbol: str, upper_price: float, lower_price: float,
                 grid_count: int, quantity: float, side: str = 'BOTH', **kwargs):
        """Initialize grid order.
        
        Args:
            client: BinanceFuturesClient instance
            symbol: Trading pair (e.g., 'BTCUSDT')
            upper_price: Upper price boundary
            lower_price: Lower price boundary
            grid_count: Number of grid levels
            quantity: Total quantity to trade
            side: 'BOTH', 'LONG', or 'SHORT'
        """
        self.client = client
        self.symbol = symbol.upper()
        self.upper_price = float(upper_price)
        self.lower_price = float(lower_price)
        self.grid_count = int(grid_count)
        self.quantity = float(quantity)
        self.side = side.upper()
        self.params = kwargs
        
        self.orders: Dict[str, dict] = {}
        self.status = 'INITIALIZED'
        self.grid_levels: List[dict] = []
        
        self._validate_inputs()
        self._calculate_grid_levels()
    
    def _validate_inputs(self):
        if self.upper_price <= self.lower_price:
            raise ValueError("Upper price must be greater than lower price")
        if self.grid_count < 2:
            raise ValueError("Grid count must be at least 2")
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.side not in ['BOTH', 'LONG', 'SHORT']:
            raise ValueError("Side must be BOTH, LONG, or SHORT")
    
    def _calculate_grid_levels(self):
        """Calculate price levels for the grid."""
        price_step = (self.upper_price - self.lower_price) / (self.grid_count - 1)
        qty_per_level = self.quantity / (self.grid_count - 1)
        
        self.grid_levels = []
        for i in range(self.grid_count):
            price = self.lower_price + (i * price_step)
            self.grid_levels.append({
                'price': round(price, 2),
                'quantity': round(qty_per_level, 6),
                'order_id': None,
                'status': 'PENDING'
            })
    
    def start(self):
        """Start the grid trading strategy."""
        self.status = 'RUNNING'
        self._place_initial_orders()
    
    def _place_initial_orders(self):
        """Place initial grid of orders."""
        for level in self.grid_levels:
            if self.side in ['BOTH', 'LONG']:
                self._place_order(level, 'BUY')
            if self.side in ['BOTH', 'SHORT'] and level['price'] > self._get_current_price():
                self._place_order(level, 'SELL')
    
    def _place_order(self, level: dict, side: str):
        """Place a single grid order."""
        try:
            order = self.client.client.futures_create_order(
                symbol=self.symbol,
                side=side,
                type='LIMIT',
                timeInForce='GTC',
                quantity=level['quantity'],
                price=level['price'],
                **self.params
            )
            level['order_id'] = order['orderId']
            level['status'] = 'ACTIVE'
            level['side'] = side
        except Exception as e:
            print(f"Error placing {side} order at {level['price']}: {e}")
    
    def update(self):
        """Update grid orders based on market conditions."""
        self._check_filled_orders()
        self._rebalance_grid()
    
    def _check_filled_orders(self):
        """Check for filled orders and take appropriate action."""
        for level in self.grid_levels:
            if level['status'] != 'ACTIVE' or not level['order_id']:
                continue
                
            try:
                order = self.client.client.futures_get_order(
                    symbol=self.symbol,
                    orderId=level['order_id']
                )
                
                if order['status'] == 'FILLED':
                    level['status'] = 'FILLED'
                    self._on_order_filled(level)
                    
            except Exception as e:
                print(f"Error checking order {level['order_id']}: {e}")
    
    def _on_order_filled(self, level: dict):
        """Handle a filled grid order."""
        # Place opposite order when a grid level is hit
        if level['side'] == 'BUY':
            self._place_order(level, 'SELL')
        else:
            self._place_order(level, 'BUY')
    
    def _rebalance_grid(self):
        """Rebalance grid orders if needed."""
        current_price = self._get_current_price()
        # Implementation depends on specific rebalancing strategy
        pass
    
    def stop(self):
        """Stop the grid trading strategy."""
        self.status = 'STOPPED'
        self._cancel_all_orders()
    
    def _cancel_all_orders(self):
        """Cancel all active grid orders."""
        try:
            self.client.client.futures_cancel_all_open_orders(symbol=self.symbol)
            for level in self.grid_levels:
                level['status'] = 'CANCELED'
                level['order_id'] = None
        except Exception as e:
            print(f"Error canceling orders: {e}")
    
    def _get_current_price(self) -> float:
        """Get current market price."""
        try:
            ticker = self.client.client.futures_symbol_ticker(symbol=self.symbol)
            return float(ticker['price'])
        except Exception as e:
            print(f"Error getting price: {e}")
            return 0.0
    
    def get_status(self) -> dict:
        """Get current grid status."""
        return {
            'status': self.status,
            'grid_levels': self.grid_levels,
            'current_price': self._get_current_price()
        }
