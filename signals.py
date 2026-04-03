"""
signals.py — Signalgenerering med candlestick-mönster (Tier 1) + RSI/MACD-bekräftelse.

Logik:
  1. Prioritet 1-mönster (Morning Star, Hammer → BUY | Dark Cloud Cover, Tweezer Top → SELL)
     kräver RSI/MACD-bekräftelse i samma riktning för att aktivera en trade.
  2. Om inget Tier-1-mönster är aktivt faller vi tillbaka på ren RSI/MACD-logik
     (kräver cfg.MIN_SIGNALS samstämmiga indikatorer).
"""

import pandas as pd
import numpy as np

from patterns import (
    detect_morning_star,
    detect_hammer,
    detect_dark_cloud_cover,
    detect_tweezer_top,
)


# ---------------------------------------------------------------------------
# Tekniska indikatorer
# ---------------------------------------------------------------------------

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
    golden = (float(macd_line.iloc[-1]) > float(signal_line.iloc[-1]) and
              float(macd_line.iloc[-2]) <= float(signal_line.iloc[-2]))
    death  = (float(macd_line.iloc[-1]) < float(signal_line.iloc[-1]) and
              float(macd_line.iloc[-2]) >= float(signal_line.iloc[-2]))
    return {
        "macd":      float(macd_line.iloc[-1]),
        "signal":    float(signal_line.iloc[-1]),
        "histogram": float(histogram.iloc[-1]),
        "golden":    golden,
        "death":     death,
        "bullish":   float(macd_line.iloc[-1]) > float(signal_line.iloc[-1]),
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


# ---------------------------------------------------------------------------
# Bekräftelseregler
# ---------------------------------------------------------------------------

def _confirmed_buy(rsi: float, macd: dict, cfg) -> tuple[bool, list[str]]:
    """
    RSI/MACD pekar uppåt:
      - RSI under overbought-nivå (rum kvar att stiga)
      - MACD-linjen är bullish (ovan signal) ELLER RSI är oversold
    """
    confirms = []
    if rsi < cfg.RSI_OVERBOUGHT:
        confirms.append(f"RSI={rsi:.1f}<{cfg.RSI_OVERBOUGHT}")
    if macd["bullish"]:
        confirms.append("MACD bullish")
    elif rsi < cfg.RSI_OVERSOLD:
        confirms.append(f"RSI oversold={rsi:.1f}")
    # Kräver RSI-utrymme OCH minst en MACD/RSI-bekräftelse
    ok = rsi < cfg.RSI_OVERBOUGHT and (macd["bullish"] or rsi < cfg.RSI_OVERSOLD)
    return ok, confirms


def _confirmed_sell(rsi: float, macd: dict, cfg) -> tuple[bool, list[str]]:
    """
    RSI/MACD pekar nedåt:
      - RSI över oversold-nivå (rum kvar att sjunka)
      - MACD-linjen är bearish (under signal) ELLER RSI är overbought
    """
    confirms = []
    if rsi > cfg.RSI_OVERSOLD:
        confirms.append(f"RSI={rsi:.1f}>{cfg.RSI_OVERSOLD}")
    if not macd["bullish"]:
        confirms.append("MACD bearish")
    elif rsi > cfg.RSI_OVERBOUGHT:
        confirms.append(f"RSI overbought={rsi:.1f}")
    ok = rsi > cfg.RSI_OVERSOLD and (not macd["bullish"] or rsi > cfg.RSI_OVERBOUGHT)
    return ok, confirms


# ---------------------------------------------------------------------------
# Huvud-funktion
# ---------------------------------------------------------------------------

def get_signal(symbol: str, bars: list[dict], cfg) -> dict:
    """
    bars: lista av {"open": f, "high": f, "low": f, "close": f, "volume": f}
          sorterad stigande på tid (äldst först).

    Returnerar direction = "BUY" | "SELL" | "HOLD" samt metadata.
    """
    closes = pd.Series([b["close"] for b in bars], dtype=float)

    if len(closes) < cfg.BB_PERIOD + 10:
        return {
            "symbol": symbol, "direction": "HOLD", "score": 0,
            "buy_signals": [], "sell_signals": [],
            "pattern": None, "rsi": None, "macd": {}, "bb": {},
        }

    rsi  = _rsi(closes, cfg.RSI_PERIOD)
    macd = _macd(closes, cfg.MACD_FAST, cfg.MACD_SLOW, cfg.MACD_SIGNAL_PERIOD)
    bb   = _bollinger(closes, cfg.BB_PERIOD, cfg.BB_STD)

    # ------------------------------------------------------------------
    # Steg 1 — Prioritet 1-mönster med RSI/MACD-bekräftelse
    # ------------------------------------------------------------------

    # BUY-mönster
    for pattern_name, detector in [("Morning Star", detect_morning_star),
                                    ("Hammer",       detect_hammer)]:
        if detector(bars):
            ok, confirms = _confirmed_buy(rsi, macd, cfg)
            if ok:
                return {
                    "symbol":      symbol,
                    "direction":   "BUY",
                    "score":       2,
                    "buy_signals": [pattern_name] + confirms,
                    "sell_signals": [],
                    "pattern":     pattern_name,
                    "rsi":         rsi,
                    "macd":        macd,
                    "bb":          bb,
                }

    # SELL-mönster
    for pattern_name, detector in [("Dark Cloud Cover", detect_dark_cloud_cover),
                                    ("Tweezer Top",      detect_tweezer_top)]:
        if detector(bars):
            ok, confirms = _confirmed_sell(rsi, macd, cfg)
            if ok:
                return {
                    "symbol":       symbol,
                    "direction":    "SELL",
                    "score":        -2,
                    "buy_signals":  [],
                    "sell_signals": [pattern_name] + confirms,
                    "pattern":      pattern_name,
                    "rsi":          rsi,
                    "macd":         macd,
                    "bb":           bb,
                }

    # ------------------------------------------------------------------
    # Steg 2 — Fallback: ren RSI/MACD/BB-logik (kräver MIN_SIGNALS)
    # ------------------------------------------------------------------
    buy_signals  = []
    sell_signals = []

    if rsi < cfg.RSI_OVERSOLD:
        buy_signals.append(f"RSI={rsi:.1f}<{cfg.RSI_OVERSOLD}")
    elif rsi > cfg.RSI_OVERBOUGHT:
        sell_signals.append(f"RSI={rsi:.1f}>{cfg.RSI_OVERBOUGHT}")

    if macd["golden"]:
        buy_signals.append("MACD golden cross")
    elif macd["death"]:
        sell_signals.append("MACD death cross")

    if bb["below"]:
        buy_signals.append(f"BB below lower ({bb['price']:.2f}<{bb['lower']:.2f})")
    elif bb["above"]:
        sell_signals.append(f"BB above upper ({bb['price']:.2f}>{bb['upper']:.2f})")

    if len(buy_signals) >= cfg.MIN_SIGNALS:
        direction = "BUY"
    elif len(sell_signals) >= cfg.MIN_SIGNALS:
        direction = "SELL"
    else:
        direction = "HOLD"

    return {
        "symbol":       symbol,
        "direction":    direction,
        "score":        len(buy_signals) - len(sell_signals),
        "buy_signals":  buy_signals,
        "sell_signals": sell_signals,
        "pattern":      None,
        "rsi":          rsi,
        "macd":         macd,
        "bb":           bb,
    }
