"""
backtest_patterns.py — Backtesta 11 candlestick-mönster mot 2 år daglig OHLCV
från Alpaca paper API för AAPL, MSFT, NVDA, TSLA, SPY.

Utfall: nästa dags stängningsrörelse (bullish mönster → förväntar upp, bearish → förväntar ned).
Rapporterar: win rate + 95% konfidensintervall (Wilson score) per mönster per aktie.
"""

import os
import sys
import math
from datetime import date, timedelta

from dotenv import load_dotenv
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import TimeFrame

from patterns import (
    BULLISH_PATTERNS,
    BEARISH_PATTERNS,
    detect_hammer,
    detect_shooting_star,
    detect_bullish_engulfing,
    detect_bearish_engulfing,
    detect_morning_star,
    detect_evening_star,
    detect_three_white_soldiers,
    detect_dark_cloud_cover,
    detect_piercing_line,
    detect_tweezer_top,
    detect_tweezer_bottom,
)

load_dotenv()

API_KEY    = os.getenv("ALPACA_API_KEY", "")
API_SECRET = os.getenv("ALPACA_SECRET_KEY", "")
BASE_URL   = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

SYMBOLS    = ["AAPL", "MSFT", "NVDA", "TSLA", "SPY"]
YEARS_BACK = 2
WINDOW     = 10   # antal bars i lookback-fönstret för mönsterdetektering


# ---------------------------------------------------------------------------
# Wilson score konfidensintervall (95%)
# ---------------------------------------------------------------------------

def wilson_ci(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = wins / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    width  = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (max(0.0, center - width), min(1.0, center + width))


# ---------------------------------------------------------------------------
# Hämta daglig OHLCV från Alpaca
# ---------------------------------------------------------------------------

def fetch_daily_bars(api, symbol: str, start: str, end: str) -> list[dict]:
    """Returnerar lista av OHLCV-dicts sorterad stigande på datum."""
    bars = api.get_bars(
        symbol,
        TimeFrame.Day,
        start,
        end,
        adjustment="split",
        feed="iex",
    ).df

    if bars.empty:
        return []

    result = []
    for _, row in bars.iterrows():
        result.append({
            "open":   float(row["open"]),
            "high":   float(row["high"]),
            "low":    float(row["low"]),
            "close":  float(row["close"]),
            "volume": float(row["volume"]),
        })
    return result


# ---------------------------------------------------------------------------
# Kör backtest för ett symbol
# ---------------------------------------------------------------------------

ALL_PATTERNS = [
    ("Hammer",               detect_hammer,               "bullish"),
    ("Shooting Star",        detect_shooting_star,        "bearish"),
    ("Bullish Engulfing",    detect_bullish_engulfing,    "bullish"),
    ("Bearish Engulfing",    detect_bearish_engulfing,    "bearish"),
    ("Morning Star",         detect_morning_star,         "bullish"),
    ("Evening Star",         detect_evening_star,         "bearish"),
    ("Three White Soldiers", detect_three_white_soldiers, "bullish"),
    ("Dark Cloud Cover",     detect_dark_cloud_cover,     "bearish"),
    ("Piercing Line",        detect_piercing_line,        "bullish"),
    ("Tweezer Top",          detect_tweezer_top,          "bearish"),
    ("Tweezer Bottom",       detect_tweezer_bottom,       "bullish"),
]


def backtest_symbol(bars: list[dict]) -> dict:
    """
    Glider ett fönster över bars, detekterar mönster vid index i,
    kontrollerar nästa dags stängningsrörelse (index i+1).

    Returnerar {pattern_name: {"wins": int, "n": int, "direction": str}}
    """
    results = {name: {"wins": 0, "n": 0, "direction": dir_}
               for name, _, dir_ in ALL_PATTERNS}

    n_bars = len(bars)

    for i in range(WINDOW - 1, n_bars - 1):
        window = bars[max(0, i - WINDOW + 1): i + 1]
        next_bar = bars[i + 1]
        next_up = next_bar["close"] > bars[i]["close"]

        for name, fn, direction in ALL_PATTERNS:
            if fn(window):
                results[name]["n"] += 1
                if direction == "bullish" and next_up:
                    results[name]["wins"] += 1
                elif direction == "bearish" and not next_up:
                    results[name]["wins"] += 1

    return results


# ---------------------------------------------------------------------------
# Utskrift
# ---------------------------------------------------------------------------

COL_W = 23  # bredd för mönsternamn-kolumn

def print_symbol_results(symbol: str, results: dict):
    print(f"\n{'═' * 70}")
    print(f"  {symbol}")
    print(f"{'═' * 70}")
    header = f"  {'Mönster':<{COL_W}}  {'Dir':^7}  {'N':>5}  {'Win%':>6}  {'95% CI':^15}"
    print(header)
    print(f"  {'-' * (COL_W)}  {'-' * 7}  {'-' * 5}  {'-' * 6}  {'-' * 15}")

    for name, _, direction in ALL_PATTERNS:
        r = results[name]
        n = r["n"]
        wins = r["wins"]
        if n == 0:
            ci_str = "  —  "
            wr_str = "   —  "
        else:
            wr = wins / n * 100
            lo, hi = wilson_ci(wins, n)
            ci_str = f"[{lo*100:4.1f}%–{hi*100:4.1f}%]"
            wr_str = f"{wr:5.1f}%"

        arrow = "▲" if direction == "bullish" else "▼"
        print(f"  {name:<{COL_W}}  {arrow:^7}  {n:>5}  {wr_str:>6}  {ci_str:^15}")


def print_summary(all_results: dict[str, dict]):
    """Aggregerad tabell: win rate per mönster over alla aktier."""
    print(f"\n\n{'═' * 70}")
    print("  AGGREGERAT (alla aktier sammanslagna)")
    print(f"{'═' * 70}")
    header = f"  {'Mönster':<{COL_W}}  {'Dir':^7}  {'N':>6}  {'Win%':>6}  {'95% CI':^15}"
    print(header)
    print(f"  {'-' * COL_W}  {'-' * 7}  {'-' * 6}  {'-' * 6}  {'-' * 15}")

    for name, _, direction in ALL_PATTERNS:
        total_wins = sum(all_results[sym][name]["wins"] for sym in all_results)
        total_n    = sum(all_results[sym][name]["n"]    for sym in all_results)

        if total_n == 0:
            ci_str = "  —  "
            wr_str = "   —  "
        else:
            wr = total_wins / total_n * 100
            lo, hi = wilson_ci(total_wins, total_n)
            ci_str = f"[{lo*100:4.1f}%–{hi*100:4.1f}%]"
            wr_str = f"{wr:5.1f}%"

        arrow = "▲" if direction == "bullish" else "▼"
        print(f"  {name:<{COL_W}}  {arrow:^7}  {total_n:>6}  {wr_str:>6}  {ci_str:^15}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not API_KEY or not API_SECRET:
        print("ERROR: ALPACA_API_KEY / ALPACA_SECRET_KEY saknas i .env")
        sys.exit(1)

    api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL)

    end_date   = date.today() - timedelta(days=1)          # igår (marknaden stängd)
    start_date = end_date - timedelta(days=365 * YEARS_BACK + 10)  # 2 år + marginal
    start_str  = start_date.isoformat()
    end_str    = end_date.isoformat()

    print(f"Backtest: {start_str} → {end_str}")
    print(f"Symboler: {', '.join(SYMBOLS)}")
    print(f"Mönster:  {len(ALL_PATTERNS)}")

    all_results: dict[str, dict] = {}

    for symbol in SYMBOLS:
        print(f"\nHämtar {symbol}...", end=" ", flush=True)
        bars = fetch_daily_bars(api, symbol, start_str, end_str)
        print(f"{len(bars)} dagar hämtade.")

        if len(bars) < WINDOW + 1:
            print(f"  VARNING: för lite data för {symbol}, hoppar över.")
            continue

        results = backtest_symbol(bars)
        all_results[symbol] = results
        print_symbol_results(symbol, results)

    if all_results:
        print_summary(all_results)

    print(f"\n{'═' * 70}")
    print("Klar.")


if __name__ == "__main__":
    main()
