# Binance Futures Order Bot

A powerful CLI-based trading bot for Binance USDT-M Futures with support for multiple order types, position management, and risk controls.

## Features

### Supported Order Types
- **Market Orders**: Immediate execution at best available price
- **Limit Orders**: Buy/sell at a specific price or better
- **Stop-Limit Orders**: Trigger a limit order when price reaches a stop price
- **OCO (One-Cancels-Other)**: Place two orders, if one executes the other is canceled
- **TWAP (Time-Weighted Average Price)**: Split large orders into smaller chunks over time
- **Grid Orders**: Place multiple limit orders at predefined price levels

### Key Features
- Support for both long and short positions
- Adjustable leverage
- Comprehensive error handling and input validation
- Detailed logging to `bot.log`
- Configurable via environment variables
- Tested with Binance Testnet

## Table of Contents
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Market Orders](#market-orders)
  - [Limit Orders](#limit-orders)
  - [Advanced Orders](#advanced-orders)
- [Logging](#logging)
- [Security](#security)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## Installation

### Prerequisites
- Python 3.8 or higher
- Binance Futures account
- API key with trading permissions

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/binance-futures-order-bot.git
   cd binance-futures-order-bot
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure your API keys:
   - Copy `.env.example` to `.env`
   - Add your Binance API key and secret

## Usage

### Market Order
```bash
python src/market_orders.py BTCUSDT BUY 0.01
```

### Limit Order
```bash
python src/limit_orders.py BTCUSDT BUY 50000 0.01
```

### Advanced Orders
Check the respective files in the `src/advanced/` directory for usage examples.

## Logging
All activities are logged to `bot.log` in the project root directory.

## Project Structure
```
binance-futures-bot/
├── src/
│   ├── __init__.py
│   ├── market_orders.py
│   ├── limit_orders.py
│   └── advanced/
│       ├── __init__.py
│       ├── oco.py
│       ├── stop_limit.py
│       ├── twap.py
│       └── grid.py
├── .env.example
├── requirements.txt
├── README.md
└── bot.log
```

## Security

- Never share your API keys
- Use environment variables for sensitive information
- Enable IP restrictions on your Binance API keys

## License

MIT
