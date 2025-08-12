#!/usr/bin/env python3
"""
Binance Futures Market Order Script

This script allows placing market orders on Binance Futures through the command line.

Usage:
    python market_orders.py <symbol> <side> <quantity> [--testnet] [--leverage LEVERAGE]

Example:
    python market_orders.py BTCUSDT BUY 0.01
    python market_orders.py ETHUSDT SELL 0.1 --testnet --leverage 10
"""
import argparse
import logging
import os
import sys
from decimal import Decimal, InvalidOperation

# Add parent directory to path to allow importing from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.client import BinanceFuturesClient
from src.config import setup_logger, logger

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Place a market order on Binance Futures')
    
    # Required arguments
    parser.add_argument('symbol', type=str, help='Trading pair symbol (e.g., BTCUSDT)')
    parser.add_argument('side', type=str, choices=['BUY', 'SELL'], help='Order side: BUY or SELL')
    parser.add_argument('quantity', type=str, help='Order quantity in base asset')
    
    # Optional arguments
    parser.add_argument('--testnet', action='store_true', help='Use Binance testnet')

    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    return parser.parse_args()

def validate_quantity(quantity_str):
    """Validate and convert quantity string to float."""
    try:
        # Use Decimal for precise decimal arithmetic
        quantity = Decimal(quantity_str)
        if quantity <= 0:
            raise ValueError("Quantity must be greater than 0")
        return float(quantity)
    except (ValueError, InvalidOperation) as e:
        raise ValueError(f"Invalid quantity: {quantity_str}. Must be a positive number.") from e

def main():
    """Main function to execute the market order."""
    try:
        # Parse command line arguments
        args = parse_args()
        
        # Set up logging
        logger = setup_logger('market_orders')
        if args.debug:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
        
        # Validate and convert quantity
        try:
            quantity = validate_quantity(args.quantity)
        except ValueError as e:
            logger.error(f"Error: {e}")
            return 1
        
        # Initialize the client
        client = BinanceFuturesClient(testnet=args.testnet)
        
        try:
            if args.testnet:
                # For testnet, use create_test_order
                result = client.client.create_test_order(
                    symbol=args.symbol.upper(),
                    side=args.side.upper(),
                    type='MARKET',
                    quantity=quantity
                )
                logger.info("Test order placed successfully")
                logger.info("This was a test order - no actual order was placed")
                return 0
            else:
                # For production, use futures_create_order
                result = client.client.futures_create_order(
                    symbol=args.symbol.upper(),
                    side=args.side.upper(),
                    type='MARKET',
                    quantity=quantity,
                    newOrderRespType='FULL'
                )
                
                logger.info("Order executed successfully!")
                logger.info(f"Order ID: {result['orderId']}")
                logger.info(f"Filled Quantity: {result.get('executedQty', 0)}")
                logger.info(f"Average Price: {result.get('avgPrice', 'N/A')}")
                return 0
                
        except Exception as e:
            error_msg = str(e).lower()
            
            # Handle common API errors
            if 'insufficient balance' in error_msg:
                logger.error("Insufficient balance for this order")
            elif 'quantity less than or equal to zero' in error_msg:
                logger.error("Order quantity must be greater than zero")
                return 1
            elif 'min notional' in error_msg:
                logger.error(f"Order value below minimum notional: {e}")
                return 1
            else:
                # Log other errors
                logger.error(f"Failed to place market order: {e}")
                return 1
        
        logger.info(f"Order executed successfully!")
        logger.info(f"Order ID: {response['orderId']}")
        logger.info(f"Filled Quantity: {response['executedQty']}")
        logger.info(f"Average Price: {response['avgPrice']}")
        logger.info(f"Commission: {response['commission']} USDT")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Order placement cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Error placing order: {e}", exc_info=args.debug)
        return 1

if __name__ == "__main__":
    sys.exit(main())
