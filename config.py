import os
from dotenv import load_dotenv

load_dotenv()

ALPACA_API_KEY    = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_BASE_URL   = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

PAPER = "paper-api.alpaca.markets" in ALPACA_BASE_URL

SYMBOLS = ["AAPL", "MSFT", "NVDA", "TSLA", "SPY"]

MAX_POSITIONS   = 5
POSITION_PCT    = 0.10
STOP_LOSS_PCT   = 0.05
TAKE_PROFIT_PCT = 0.15
MIN_SIGNALS     = 1      # 1 av 3 räcker i fallback-läget

RSI_PERIOD        = 14
RSI_OVERSOLD      = 30
RSI_OVERBOUGHT    = 70
MACD_FAST         = 12
MACD_SLOW         = 26
MACD_SIGNAL_PERIOD = 9
BB_PERIOD         = 20
BB_STD            = 2.0
BARS_NEEDED       = 60

LOOP_INTERVAL_SEC  = 300
MARKET_OPEN_ET     = (9, 30)
MARKET_CLOSE_ET    = (16, 0)
