import os
from dotenv import load_dotenv

load_dotenv()

ALPACA_API_KEY    = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_BASE_URL   = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

PAPER = "paper-api.alpaca.markets" in ALPACA_BASE_URL

# Symboler att bevaka
SYMBOLS = ["AAPL", "MSFT", "NVDA", "TSLA", "SPY"]

# Portföljrisk
MAX_POSITIONS       = 5      # max antal öppna positions
POSITION_PCT        = 0.10   # 10% av portfolio per trade
STOP_LOSS_PCT       = 0.05   # -5% stop-loss
TAKE_PROFIT_PCT     = 0.15   # +15% take-profit
MIN_SIGNALS         = 2      # minst 2 av 3 indikatorer för trade

# Tekniska indikatorer
RSI_PERIOD          = 14
RSI_OVERSOLD        = 30
RSI_OVERBOUGHT      = 70
MACD_FAST           = 12
MACD_SLOW           = 26
MACD_SIGNAL_PERIOD  = 9
BB_PERIOD           = 20
BB_STD              = 2.0
BARS_NEEDED         = 60     # ~1 månad daglig data + marginal

# Loop
LOOP_INTERVAL_SEC   = 300    # var 5:e minut
MARKET_OPEN_ET      = (9, 30)
MARKET_CLOSE_ET     = (16, 0)
