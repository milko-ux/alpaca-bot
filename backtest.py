"""
backtest.py — Skannar historisk data och visar alla dagar där mönster + signal triggas.
Användning: python3 backtest.py
"""

from datetime import datetime, timezone, timedelta
import alpaca_trade_api as tradeapi
import config as cfg
from patterns import detect_all
from signals import get_signal

api = tradeapi.REST(cfg.ALPACA_API_KEY, cfg.ALPACA_SECRET_KEY,
                    cfg.ALPACA_BASE_URL, api_version="v2")

def fetch_bars(symbol):
    end   = datetime.now(timezone.utc)
    start = end - timedelta(days=120)
    df = api.get_bars(symbol, "1Day",
                      start=start.strftime("%Y-%m-%d"),
                      end=end.strftime("%Y-%m-%d"),
                      limit=120, feed="iex").df
    if df.empty:
        return []
    bars = []
    for ts, row in df.iterrows():
        bars.append({
            "date":   str(ts)[:10],
            "open":   float(row["open"]),
            "high":   float(row["high"]),
            "low":    float(row["low"]),
            "close":  float(row["close"]),
            "volume": float(row["volume"]),
        })
    return bars

print(f"\n{'='*65}")
print(f"  BACKTEST — senaste 120 dagar")
print(f"  Körs: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"{'='*65}\n")

total_buy = 0
total_sell = 0

for symbol in cfg.SYMBOLS:
    bars = fetch_bars(symbol)
    if len(bars) < 10:
        print(f"{symbol}: för få bars\n")
        continue

    hits = []

    # Skanna varje dag (från dag 5 till idag)
    for i in range(5, len(bars)):
        window = bars[:i+1]          # alla bars upp till och med dag i
        date   = bars[i]["date"]

        patterns = detect_all(window)

        # Bygg bars utan datum för get_signal
        clean = [{"open": b["open"], "high": b["high"],
                  "low": b["low"], "close": b["close"],
                  "volume": b["volume"]} for b in window]
        sig = get_signal(symbol, clean, cfg)

        if patterns["bullish"] or patterns["bearish"] or sig["direction"] != "HOLD":
            hits.append({
                "date":     date,
                "bullish":  patterns["bullish"],
                "bearish":  patterns["bearish"],
                "signal":   sig["direction"],
                "rsi":      sig["rsi"],
                "macd":     "bull" if sig["macd"].get("bullish") else "bear",
                "reasons":  sig["buy_signals"] + sig["sell_signals"],
            })

    print(f"{'─'*65}")
    print(f"  {symbol} — {len(hits)} träffar av {len(bars)} dagar skannade")
    print()

    buy_hits  = [h for h in hits if h["signal"] == "BUY"]
    sell_hits = [h for h in hits if h["signal"] == "SELL"]
    total_buy  += len(buy_hits)
    total_sell += len(sell_hits)

    for h in hits[-15:]:   # visa senaste 15 träffar
        arrow = "🟢 BUY " if h["signal"] == "BUY" else \
                "🔴 SELL" if h["signal"] == "SELL" else "⬜ HOLD"
        bull = f" mönster:{','.join(h['bullish'])}" if h["bullish"] else ""
        bear = f" mönster:{','.join(h['bearish'])}" if h["bearish"] else ""
        rsi  = f"RSI={h['rsi']:.1f}" if h["rsi"] else "RSI=N/A"
        print(f"  {h['date']}  {arrow}  {rsi}  MACD={h['macd']}"
              f"{bull}{bear}")
        if h["reasons"]:
            print(f"             → {', '.join(h['reasons'])}")
    print()

print(f"{'='*65}")
print(f"  TOTALT: {total_buy} BUY-signaler  |  {total_sell} SELL-signaler")
print(f"  över alla {len(cfg.SYMBOLS)} symboler senaste 120 dagarna")
print(f"{'='*65}\n")
