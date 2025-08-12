import os
from binance.client import Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API credentials
api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')

try:
    # Initialize testnet client
    client = Client(
        api_key=api_key,
        api_secret=api_secret,
        testnet=True,
        tld='com'
    )
    
    # Test connection
    print("Testing connection to Binance Futures Testnet...")
    
    # Test server time
    time = client.get_server_time()
    print("\nServer Time:", time)
    
    # Test market data
    btc_price = client.get_symbol_ticker(symbol='BTCUSDT')
    
    # Test account status (using spot endpoint since futures_account_status doesn't exist)
    account = client.get_account()
    print("\nAccount Status:", account['canTrade'])
    print("\nBTC/USDT Price:", btc_price)
    
except Exception as e:
    print("\nError:", str(e))
    print("\nTroubleshooting Steps:")
    print("1. Make sure you're using a testnet API key (not mainnet)")
    print("2. Verify the API key has 'Enable Futures' permission")
    print("3. Check if your IP is whitelisted in the API settings")
    print("4. Try creating a new API key from the testnet site")
