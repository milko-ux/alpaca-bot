import os
from dotenv import load_dotenv

load_dotenv()

ALPACA_API_KEY    = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_BASE_URL   = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

# Trading parameters
DRY_RUN           = ALPACA_BASE_URL == "https://paper-api.alpaca.markets"
SYMBOLS           = ["AAPL", "TSLA", "NVDA", "SPY", "QQQ"]
TRADE_AMOUNT_USD  = 100.0   # dollars per trade
RSI_PERIOD        = 14
RSI_OVERSOLD      = 30
RSI_OVERBOUGHT    = 70
MACD_FAST         = 12
MACD_SLOW         = 26
MACD_SIGNAL       = 9
BB_PERIOD         = 20
BB_STD            = 2.0
LOOP_INTERVAL_SEC = 60
