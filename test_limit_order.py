"""Test script for limit orders with simplified imports."""
import os
import sys
import logging
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, os.path.abspath('.'))

# Import directly from the src directory
from src.client import BinanceFuturesClient
from src.spot_client import BinanceSpotClient
from src.config import setup_logger, logger

def main():
    try:
        # Initialize logger
        logger = setup_logger('test_limit_order')
        
        # Test spot client
        logger.info("Initializing Spot Client...")
        spot_client = BinanceSpotClient(testnet=True)
        logger.info("Spot Client initialized successfully!")
        
        # Test futures client
        logger.info("Initializing Futures Client...")
        futures_client = BinanceFuturesClient(testnet=True)
        logger.info("Futures Client initialized successfully!")
        
        # Test order parameters
        symbol = "BTCUSDT"
        side = "BUY"
        quantity = Decimal("0.001")
        price = Decimal("50000.0")
        
        logger.info(f"Test parameters: {side} {quantity} {symbol} @ {price}")
        
        # Test placing a limit order on Spot Testnet
        logger.info("Placing test limit order on Spot Testnet...")
        spot_order = spot_client.client.create_test_order(
            symbol=symbol,
            side=side,
            type='LIMIT',
            timeInForce='GTC',
            quantity=float(quantity),
            price=str(price)
        )
        logger.info("Spot Test order placed successfully!")
        logger.info(f"Spot Order response: {spot_order}")
        
        # Test Futures connection with a simple API call
        logger.info("Testing Futures connection...")
        try:
            # Try a simple non-trading endpoint
            futures_info = futures_client.client.futures_exchange_info()
            logger.info("Futures connection successful!")
            logger.info(f"Futures server time: {futures_info.get('serverTime')}")
            
            # Try to get account balance
            try:
                balance = futures_client.client.futures_account_balance()
                usdt_balance = next((item for item in balance if item['asset'] == 'USDT'), None)
                if usdt_balance:
                    logger.info(f"Futures USDT Balance: {usdt_balance['balance']}")
            except Exception as balance_error:
                logger.warning(f"Could not fetch Futures balance: {balance_error}")
                
        except Exception as e:
            logger.error(f"Futures connection failed: {e}")
            logger.info("Note: This is expected if your API keys don't have Futures permissions.")
            logger.info("To enable Futures trading, you'll need to create a new API key with Futures permissions.")
        
        # Test placing a real spot limit order (commented out for safety)
        # logger.info("Placing real limit order on Spot Testnet...")
        # order = spot_client.client.create_order(
        #     symbol=symbol,
        #     side=side,
        #     type='LIMIT',
        #     timeInForce='GTC',
        #     quantity=float(quantity),
        #     price=str(price)
        # )
        # logger.info(f"Order placed successfully! Order ID: {order['orderId']}")
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
