#!/usr/bin/env python3
"""
Binance Futures Limit Order Script

This script allows placing limit orders on Binance Futures through the command line.

Usage:
    python limit_orders.py <symbol> <side> <quantity> <price> [--testnet] [--leverage LEVERAGE] [--time-in-force TIME_IN_FORCE]

Example:
    python limit_orders.py BTCUSDT BUY 0.01 50000
    python limit_orders.py ETHUSDT SELL 0.1 2000 --testnet --leverage 10 --time-in-force GTC

Time in Force Options:
    - GTC (Good Till Cancel): Order will remain on the book until filled or canceled
    - IOC (Immediate or Cancel): Order will be filled immediately and completely or not at all
    - FOK (Fill or Kill): Order will be filled immediately and completely or canceled
    - GTX (Good Till Crossing, Post-Only): Order will be a maker order or canceled
"""
import argparse
import logging
import os
import sys
from decimal import Decimal, InvalidOperation

# Add parent directory to path to allow importing from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from src.client import BinanceFuturesClient
    from src.spot_client import BinanceSpotClient
    from src.config import setup_logger, logger
except ImportError as e:
    # Fallback to direct imports if running as __main__
    import sys
    import os
    sys.path.insert(0, os.path.abspath('.'))
    from client import BinanceFuturesClient
    from spot_client import BinanceSpotClient
    from config import setup_logger, logger

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Place a limit order on Binance Futures')
    
    # Required arguments
    parser.add_argument('symbol', type=str, help='Trading pair symbol (e.g., BTCUSDT)')
    parser.add_argument('side', type=str, choices=['BUY', 'SELL'], help='Order side: BUY or SELL')
    parser.add_argument('quantity', type=str, help='Order quantity in base asset')
    parser.add_argument('price', type=str, help='Limit price for the order')
    
    # Optional arguments
    parser.add_argument('--testnet', action='store_true', help='Use Binance testnet')
    parser.add_argument('--leverage', type=int, default=10, help='Leverage (default: 10)')
    parser.add_argument('--time-in-force', type=str, default='GTC', 
                       choices=['GTC', 'IOC', 'FOK', 'GTX'],
                       help='Time in force (default: GTC)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    return parser.parse_args()

def validate_decimal(value_str, name):
    """Validate and convert string to float with proper error handling."""
    try:
        # Use Decimal for precise decimal arithmetic
        value = Decimal(value_str)
        if value <= 0:
            raise ValueError(f"{name} must be greater than 0")
        return float(value)
    except (ValueError, InvalidOperation) as e:
        raise ValueError(f"Invalid {name.lower()}: {value_str}. Must be a positive number.") from e

def main():
    """Main function to execute the limit order."""
    try:
        # Parse command line arguments
        args = parse_args()
        
        # Configure logging
        logger = setup_logger('limit_orders')
        if args.debug:
            logger.setLevel(logging.DEBUG)
        
        # Validate and convert quantity and price
        try:
            quantity = validate_decimal(args.quantity, 'Quantity')
            price = validate_decimal(args.price, 'Price')
        except ValueError as e:
            logger.error(f"Error: {e}")
            return 1
        
        logger.info(f"Placing {args.side} limit order for {quantity} {args.symbol} @ {price}")
        
        # Initialize client based on testnet setting
        if args.testnet:
            from spot_client import BinanceSpotClient
            client = BinanceSpotClient(testnet=True)
            logger.info("Using Spot Test Network")
            
            # Prepare Spot order parameters
            order_params = {
                'symbol': args.symbol.upper(),
                'side': args.side.upper(),
                'type': 'LIMIT',
                'timeInForce': args.time_in_force,
                'quantity': quantity,
                'price': str(price),  # Convert to string to avoid floating point precision issues
                'newOrderRespType': 'FULL'
            }
        else:
            # Initialize Futures client
            client = BinanceFuturesClient(testnet=False)
            logger.info("Using Futures Mainnet")
            
            # Set leverage if specified
            if args.leverage:
                try:
                    client.client.futures_change_leverage(
                        symbol=args.symbol,
                        leverage=args.leverage
                    )
                    logger.info(f"Set leverage to {args.leverage}x for {args.symbol}")
                except Exception as e:
                    logger.warning(f"Failed to set leverage: {e}")
            
            # Prepare Futures order parameters
            order_params = {
                'symbol': args.symbol,
                'side': args.side,
                'type': 'LIMIT',
                'timeInForce': args.time_in_force,
                'quantity': quantity,
                'price': str(price),  # Convert to string to avoid floating point precision issues
            }
        
        # Place the limit order
        if args.testnet:
            # For testnet, use create_test_order (Spot)
            result = client.client.create_test_order(**order_params)
            logger.info("Test order placed successfully")
            logger.info("This was a test order - no actual order was placed")
            logger.info(f"Order parameters: {order_params}")
        else:
            # For production, use futures_create_order
            result = client.client.futures_create_order(**order_params)
            
            logger.info(f"Order placed successfully!")
            logger.info(f"Order ID: {result['orderId']}")
            logger.info(f"Status: {result.get('status', 'N/A')}")
            logger.info(f"Price: {result.get('price', 'N/A')}")
            logger.info(f"Quantity: {result.get('origQty', 'N/A')}")
            
            # Additional details for limit orders
            if 'executedQty' in result:
                logger.info(f"Filled Quantity: {result['executedQty']}")
            if 'cummulativeQuoteQty' in result:
                logger.info(f"Filled Amount: {result['cummulativeQuoteQty']} USDT")
        
        return 0
        
    except Exception as e:
        error_msg = str(e).lower()
        
        # Handle common API errors
        if 'insufficient balance' in error_msg:
            logger.error("Insufficient balance for this order")
        elif 'price less than' in error_msg or 'price greater than' in error_msg:
            logger.error("Invalid price. Check the price filter for this symbol.")
        elif 'quantity less than' in error_msg or 'quantity greater than' in error_msg:
            logger.error("Invalid quantity. Check the lot size for this symbol.")
        elif 'precision' in error_msg:
            logger.error("Precision error. Check the quantity and price precision for this symbol.")
        elif 'leverage' in error_msg:
            logger.error("Leverage error. Check if the leverage is within allowed range.")
        else:
            logger.error(f"Failed to place order: {e}")
            
        return 1
        logger.info(f"Status: {order.status}")
        logger.info(f"Quantity: {order.quantity}")
        logger.info(f"Price: {order.price}")
        
        if order.filled_quantity > 0:
            logger.info(f"Filled Quantity: {order.filled_quantity}")
            logger.info(f"Average Price: {order.filled_price}")
            logger.info(f"Commission: {order.commission} USDT")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Order placement cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Error placing order: {e}", exc_info=args.debug if 'args' in locals() else False)
        return 1

if __name__ == "__main__":
    sys.exit(main())
