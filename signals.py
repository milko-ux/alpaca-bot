import pandas as pd
import numpy as np


def rsi(closes: pd.Series, period: int = 14) -> float:
    """Returnerar senaste RSI-värdet."""
    delta = closes.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    rsi_s = 100 - (100 / (1 + rs))
    return float(rsi_s.iloc[-1])


def macd(closes: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """Returnerar MACD-linje, signal-linje och histogram."""
    ema_fast   = closes.ewm(span=fast,   adjust=False).mean()
    ema_slow   = closes.ewm(span=slow,   adjust=False).mean()
    macd_line  = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram  = macd_line - signal_line
    return {
        "macd":      float(macd_line.iloc[-1]),
        "signal":    float(signal_line.iloc[-1]),
        "histogram": float(histogram.iloc[-1]),
        "crossover": (
            float(macd_line.iloc[-1]) > float(signal_line.iloc[-1]) and
            float(macd_line.iloc[-2]) <= float(signal_line.iloc[-2])
        ),
        "crossunder": (
            float(macd_line.iloc[-1]) < float(signal_line.iloc[-1]) and
            float(macd_line.iloc[-2]) >= float(signal_line.iloc[-2])
        ),
    }


def bollinger_bands(closes: pd.Series, period: int = 20, std: float = 2.0) -> dict:
    """Returnerar övre, mitten och nedre Bollinger Band samt position."""
    sma   = closes.rolling(period).mean()
    sigma = closes.rolling(period).std()
    upper = sma + std * sigma
    lower = sma - std * sigma
    price = float(closes.iloc[-1])
    return {
        "upper":    float(upper.iloc[-1]),
        "middle":   float(sma.iloc[-1]),
        "lower":    float(lower.iloc[-1]),
        "price":    price,
        "above":    price > float(upper.iloc[-1]),
        "below":    price < float(lower.iloc[-1]),
        "pct":      (price - float(lower.iloc[-1])) / (float(upper.iloc[-1]) - float(lower.iloc[-1]) + 1e-9),
    }


def get_signal(symbol: str, closes: pd.Series, cfg) -> dict:
    """
    Kombinerar RSI, MACD och Bollinger Bands till en köp/sälj-signal.
    Returnerar: {"symbol", "direction": "BUY"|"SELL"|"HOLD", "score": int, "rsi", "macd", "bb"}
    """
    if len(closes) < cfg.BB_PERIOD + 5:
        return {"symbol": symbol, "direction": "HOLD", "score": 0, "reason": "för lite data"}

    r  = rsi(closes, cfg.RSI_PERIOD)
    m  = macd(closes, cfg.MACD_FAST, cfg.MACD_SLOW, cfg.MACD_SIGNAL)
    bb = bollinger_bands(closes, cfg.BB_PERIOD, cfg.BB_STD)

    buy_score  = 0
    sell_score = 0

    # RSI
    if r < cfg.RSI_OVERSOLD:
        buy_score += 1
    elif r > cfg.RSI_OVERBOUGHT:
        sell_score += 1

    # MACD
    if m["crossover"]:
        buy_score += 2
    elif m["crossunder"]:
        sell_score += 2
    elif m["macd"] > m["signal"]:
        buy_score += 1
    elif m["macd"] < m["signal"]:
        sell_score += 1

    # Bollinger Bands
    if bb["below"]:
        buy_score += 1
    elif bb["above"]:
        sell_score += 1

    score     = buy_score - sell_score
    direction = "BUY" if score >= 2 else ("SELL" if score <= -2 else "HOLD")

    return {
        "symbol":    symbol,
        "direction": direction,
        "score":     score,
        "rsi":       r,
        "macd":      m,
        "bb":        bb,
    }
