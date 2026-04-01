import time
from datetime import datetime

import pandas as pd
import alpaca_trade_api as tradeapi

import config as cfg
from signals import get_signal
from executor import execute, api


def fetch_closes(symbol: str, limit: int = 100) -> pd.Series:
    """Hämtar dagliga stängningspriser för en symbol."""
    bars = api.get_bars(symbol, "1Day", limit=limit).df
    if bars.empty:
        return pd.Series(dtype=float)
    return bars["close"].astype(float)


def is_market_open() -> bool:
    try:
        clock = api.get_clock()
        return clock.is_open
    except Exception:
        return False


def run_loop() -> None:
    print(f"\n{'='*55}")
    print(f"[main] Loop — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[main] Läge: {'PAPER (DRY-RUN)' if cfg.DRY_RUN else 'LIVE'}")
    print(f"{'='*55}")

    if not is_market_open():
        print("[main] Marknaden är stängd — hoppar över.")
        return

    for symbol in cfg.SYMBOLS:
        closes = fetch_closes(symbol)
        if closes.empty:
            print(f"[main] {symbol}: kunde inte hämta data.")
            continue

        signal = get_signal(symbol, closes, cfg)
        rsi_v  = signal["rsi"]
        score  = signal["score"]
        bb_pct = signal["bb"]["pct"] * 100
        macd_h = signal["macd"]["histogram"]

        print(
            f"[main] {symbol:5s}  RSI={rsi_v:5.1f}  MACD_hist={macd_h:+.3f}  "
            f"BB={bb_pct:5.1f}%  score={score:+d}  → {signal['direction']}"
        )

        execute(signal)


if __name__ == "__main__":
    print(f"[main] Alpaca-bot startar ({'PAPER' if cfg.DRY_RUN else 'LIVE'})")
    print(f"[main] Symboler: {cfg.SYMBOLS}")
    print(f"[main] Insats per trade: ${cfg.TRADE_AMOUNT_USD:.2f}")
    print(f"[main] Intervall: {cfg.LOOP_INTERVAL_SEC}s\n")

    while True:
        run_loop()
        print(f"[main] Nästa körning om {cfg.LOOP_INTERVAL_SEC}s.")
        time.sleep(cfg.LOOP_INTERVAL_SEC)
