#!/usr/bin/env python3
"""
Binance Futures Advanced Orders Script

This script provides a command-line interface for advanced order types:
- Stop-Limit orders
- OCO (One-Cancels-Other) orders
- TWAP (Time-Weighted Average Price) orders
- Grid trading orders

Usage:
    python advanced_orders.py <order_type> [options]

Order Types:
    stop-limit    Place a stop-limit order
    oco           Place a One-Cancels-Other order
    twap          Execute a TWAP order
    grid          Start a grid trading strategy

Examples:
    # Stop-Limit order
    python advanced_orders.py stop-limit BTCUSDT BUY 0.01 50000 49000
    
    # OCO order
    python advanced_orders.py oco BTCUSDT BUY 0.01 50000 49000 49500
    
    # TWAP order
    python advanced_orders.py twap BTCUSDT BUY 0.1 --duration 60 --chunks 12
    
    # Grid trading
    python advanced_orders.py grid BTCUSDT 52000 48000 10 0.1 --side BOTH
"""
import argparse
import logging
import os
import sys
from datetime import datetime

# Add parent directory to path to allow importing from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from client import BinanceFuturesClient
from orders.advanced.stop_limit import StopLimitOrder
from orders.advanced.oco import OCOOrder
from orders.advanced.twap import TWAPOrder
from orders.advanced.grid import GridOrder
from config import setup_logger, logger

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Binance Futures Advanced Orders')
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # Common arguments
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument('symbol', type=str, help='Trading pair (e.g., BTCUSDT)')
    parent_parser.add_argument('--testnet', action='store_true', help='Use testnet')
    parent_parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    # Stop-Limit order
    stop_limit_parser = subparsers.add_parser('stop-limit', parents=[parent_parser], 
                                             help='Place a stop-limit order')
    stop_limit_parser.add_argument('side', type=str, choices=['BUY', 'SELL'], 
                                 help='Order side')
    stop_limit_parser.add_argument('quantity', type=float, help='Order quantity')
    stop_limit_parser.add_argument('stop_price', type=float, help='Stop price')
    stop_limit_parser.add_argument('limit_price', type=float, help='Limit price')
    stop_limit_parser.add_argument('--leverage', type=int, default=10, 
                                 help='Leverage (default: 10)')
    
    # OCO order
    oco_parser = subparsers.add_parser('oco', parents=[parent_parser],
                                      help='Place an OCO order')
    oco_parser.add_argument('side', type=str, choices=['BUY', 'SELL'], 
                          help='Order side')
    oco_parser.add_argument('quantity', type=float, help='Order quantity')
    oco_parser.add_argument('limit_price', type=float, 
                          help='Limit price (take profit)')
    oco_parser.add_argument('stop_price', type=float, 
                          help='Stop price')
    oco_parser.add_argument('stop_limit_price', type=float,
                          help='Stop limit price (stop loss)')
    oco_parser.add_argument('--leverage', type=int, default=10,
                          help='Leverage (default: 10)')
    
    # TWAP order
    twap_parser = subparsers.add_parser('twap', parents=[parent_parser],
                                       help='Execute a TWAP order')
    twap_parser.add_argument('side', type=str, choices=['BUY', 'SELL'],
                           help='Order side')
    twap_parser.add_argument('quantity', type=float, 
                           help='Total order quantity')
    twap_parser.add_argument('--duration', type=int, default=60,
                           help='Duration in minutes (default: 60)')
    twap_parser.add_argument('--chunks', type=int, default=12,
                           help='Number of chunks (default: 12)')
    twap_parser.add_argument('--price-limit', type=float,
                           help='Maximum price for BUY or minimum for SELL')
    twap_parser.add_argument('--leverage', type=int, default=10,
                           help='Leverage (default: 10)')
    
    # Grid trading
    grid_parser = subparsers.add_parser('grid', parents=[parent_parser],
                                       help='Start grid trading')
    grid_parser.add_argument('upper_price', type=float,
                           help='Upper price boundary')
    grid_parser.add_argument('lower_price', type=float,
                           help='Lower price boundary')
    grid_parser.add_argument('grid_count', type=int,
                           help='Number of grid levels')
    grid_parser.add_argument('quantity', type=float,
                           help='Total quantity to trade')
    grid_parser.add_argument('--side', type=str, default='BOTH',
                           choices=['BOTH', 'LONG', 'SHORT'],
                           help='Grid side (default: BOTH)')
    grid_parser.add_argument('--leverage', type=int, default=10,
                           help='Leverage (default: 10)')
    
    return parser.parse_args()

def main():
    """Main function to handle advanced orders."""
    try:
        args = parse_args()
        
        # Configure logging
        log_level = logging.DEBUG if args.debug else logging.INFO
        setup_logger('advanced_orders', log_level=log_level)
        
        # Initialize client
        client = BinanceFuturesClient(testnet=args.testnet)
        
        # Set leverage if specified
        if hasattr(args, 'leverage'):
            try:
                client.client.futures_change_leverage(
                    symbol=args.symbol,
                    leverage=args.leverage
                )
                logger.info(f"Set leverage to {args.leverage}x for {args.symbol}")
            except Exception as e:
                logger.warning(f"Failed to set leverage: {e}")
        
        # Handle different order types
        if args.command == 'stop-limit':
            order = StopLimitOrder(
                client=client,
                symbol=args.symbol,
                side=args.side,
                quantity=args.quantity,
                stop_price=args.stop_price,
                limit_price=args.limit_price
            )
            result = order.place()
            logger.info(f"Stop-limit order placed: {result}")
            
        elif args.command == 'oco':
            order = OCOOrder(
                client=client,
                symbol=args.symbol,
                side=args.side,
                quantity=args.quantity,
                limit_price=args.limit_price,
                stop_price=args.stop_price,
                stop_limit_price=args.stop_limit_price
            )
            result = order.place()
            logger.info(f"OCO order placed: {result}")
            
        elif args.command == 'twap':
            order = TWAPOrder(
                client=client,
                symbol=args.symbol,
                side=args.side,
                total_quantity=args.quantity,
                duration_minutes=args.duration,
                chunks=args.chunks,
                price_limit=args.price_limit
            )
            logger.info(f"Starting TWAP execution: {order}")
            result = order.execute()
            logger.info(f"TWAP execution completed: {result}")
            
        elif args.command == 'grid':
            grid = GridOrder(
                client=client,
                symbol=args.symbol,
                upper_price=args.upper_price,
                lower_price=args.lower_price,
                grid_count=args.grid_count,
                quantity=args.quantity,
                side=args.side
            )
            logger.info(f"Starting grid trading: {grid}")
            grid.start()
            
            try:
                # Keep the script running to monitor the grid
                while True:
                    time.sleep(10)
                    grid.update()
            except KeyboardInterrupt:
                logger.info("Stopping grid trading...")
                grid.stop()
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=args.debug if 'debug' in args else False)
        return 1

if __name__ == "__main__":
    import time  # Add this import at the top of the file
    sys.exit(main())
