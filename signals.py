import pandas as pd
import numpy as np


def _rsi(closes: pd.Series, period: int) -> float:
    delta = closes.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    return float((100 - 100 / (1 + rs)).iloc[-1])


def _macd(closes: pd.Series, fast: int, slow: int, sig: int) -> dict:
    ema_fast    = closes.ewm(span=fast, adjust=False).mean()
    ema_slow    = closes.ewm(span=slow, adjust=False).mean()
    macd_line   = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=sig, adjust=False).mean()
    histogram   = macd_line - signal_line
    # Golden cross: MACD korsade upp signal på senaste stången
    golden = (float(macd_line.iloc[-1]) > float(signal_line.iloc[-1]) and
              float(macd_line.iloc[-2]) <= float(signal_line.iloc[-2]))
    # Death cross: MACD korsade ned signal på senaste stången
    death  = (float(macd_line.iloc[-1]) < float(signal_line.iloc[-1]) and
              float(macd_line.iloc[-2]) >= float(signal_line.iloc[-2]))
    return {
        "macd":        float(macd_line.iloc[-1]),
        "signal":      float(signal_line.iloc[-1]),
        "histogram":   float(histogram.iloc[-1]),
        "golden":      golden,
        "death":       death,
        "bullish":     float(macd_line.iloc[-1]) > float(signal_line.iloc[-1]),
    }


def _bollinger(closes: pd.Series, period: int, std: float) -> dict:
    sma   = closes.rolling(period).mean()
    sigma = closes.rolling(period).std()
    upper = sma + std * sigma
    lower = sma - std * sigma
    price = float(closes.iloc[-1])
    band_width = float(upper.iloc[-1]) - float(lower.iloc[-1]) + 1e-9
    return {
        "upper":  float(upper.iloc[-1]),
        "middle": float(sma.iloc[-1]),
        "lower":  float(lower.iloc[-1]),
        "price":  price,
        "above":  price > float(upper.iloc[-1]),
        "below":  price < float(lower.iloc[-1]),
        "pct":    (price - float(lower.iloc[-1])) / band_width,
    }


def get_signal(symbol: str, closes: pd.Series, cfg) -> dict:
    """
    Kräver minst cfg.MIN_SIGNALS (2) samstämmiga indikatorer för BUY/SELL.
    Returnerar direction = "BUY" | "SELL" | "HOLD".
    """
    if len(closes) < cfg.BB_PERIOD + 10:
        return {
            "symbol": symbol, "direction": "HOLD", "score": 0,
            "buy_signals": [], "sell_signals": [], "rsi": None, "macd": {}, "bb": {},
        }

    r  = _rsi(closes, cfg.RSI_PERIOD)
    m  = _macd(closes, cfg.MACD_FAST, cfg.MACD_SLOW, cfg.MACD_SIGNAL_PERIOD)
    bb = _bollinger(closes, cfg.BB_PERIOD, cfg.BB_STD)

    buy_signals  = []
    sell_signals = []

    # RSI
    if r < cfg.RSI_OVERSOLD:
        buy_signals.append(f"RSI={r:.1f}<{cfg.RSI_OVERSOLD}")
    elif r > cfg.RSI_OVERBOUGHT:
        sell_signals.append(f"RSI={r:.1f}>{cfg.RSI_OVERBOUGHT}")

    # MACD
    if m["golden"]:
        buy_signals.append("MACD golden cross")
    elif m["death"]:
        sell_signals.append("MACD death cross")

    # Bollinger Bands
    if bb["below"]:
        buy_signals.append(f"BB below lower ({bb['price']:.2f}<{bb['lower']:.2f})")
    elif bb["above"]:
        sell_signals.append(f"BB above upper ({bb['price']:.2f}>{bb['upper']:.2f})")

    buy_count  = len(buy_signals)
    sell_count = len(sell_signals)

    if buy_count >= cfg.MIN_SIGNALS:
        direction = "BUY"
    elif sell_count >= cfg.MIN_SIGNALS:
        direction = "SELL"
    else:
        direction = "HOLD"

    return {
        "symbol":       symbol,
        "direction":    direction,
        "score":        buy_count - sell_count,
        "buy_signals":  buy_signals,
        "sell_signals": sell_signals,
        "rsi":          r,
        "macd":         m,
        "bb":           bb,
    }
