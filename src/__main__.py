"""Main entry point for the Binance Futures Order Bot."""
import sys

def main():
    # This allows running the package with python -m src
    from .market_orders import main as market_main
    return market_main()

if __name__ == "__main__":
    sys.exit(main())
