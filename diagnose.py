"""
diagnose.py — Kör lokalt för att testa signaler mot historisk data.
Användning: python diagnose.py
"""

from datetime import datetime, timezone, timedelta
import alpaca_trade_api as tradeapi
import config as cfg
from signals import get_signal
from patterns import detect_all

api = tradeapi.REST(cfg.ALPACA_API_KEY, cfg.ALPACA_SECRET_KEY,
                    cfg.ALPACA_BASE_URL, api_version="v2")

def fetch_bars(symbol):
    end   = datetime.now(timezone.utc)
    start = end - timedelta(days=90)
    df = api.get_bars(symbol, "1Day",
                      start=start.strftime("%Y-%m-%d"),
                      end=end.strftime("%Y-%m-%d"),
                      limit=cfg.BARS_NEEDED, feed="iex").df
    if df.empty:
        return []
    return [{"open": float(r["open"]), "high": float(r["high"]),
             "low": float(r["low"]), "close": float(r["close"]),
             "volume": float(r["volume"])} for _, r in df.iterrows()]

print(f"\n{'='*60}")
print(f"  ALPACA BOT — DIAGNOSTIK  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"{'='*60}\n")

for symbol in cfg.SYMBOLS:
    bars = fetch_bars(symbol)
    print(f"{'─'*60}")
    print(f"  {symbol}  ({len(bars)} bars hämtade)")

    if len(bars) < 5:
        print(f"  ⚠️  FÖR FÅ BARS — kan inte analysera\n")
        continue

    # Visa senaste 3 stängda bars ([-4], [-3], [-2])
    print(f"  Senaste stängda bars:")
    for i, idx in enumerate([-4, -3, -2]):
        b = bars[idx]
        direction = "▲" if b["close"] > b["open"] else "▼"
        print(f"    [{i+1}] {direction} O={b['open']:.2f} H={b['high']:.2f} "
              f"L={b['low']:.2f} C={b['close']:.2f}")

    # Mönster
    patterns = detect_all(bars)
    if patterns["bullish"]:
        print(f"  🟢 Bullish mönster: {', '.join(patterns['bullish'])}")
    if patterns["bearish"]:
        print(f"  🔴 Bearish mönster: {', '.join(patterns['bearish'])}")
    if not patterns["bullish"] and not patterns["bearish"]:
        print(f"  ⬜ Inga mönster detekterade")

    # Signal
    sig = get_signal(symbol, bars, cfg)
    arrow = "🟢 BUY" if sig["direction"] == "BUY" else \
            "🔴 SELL" if sig["direction"] == "SELL" else "⬜ HOLD"
    rsi_str = f"{sig['rsi']:.1f}" if sig["rsi"] else "N/A"
    print(f"  RSI={rsi_str}  MACD={'bullish' if sig['macd'].get('bullish') else 'bearish'}")
    print(f"  → Signal: {arrow}  (score={sig['score']})")
    if sig["buy_signals"]:
        print(f"    BUY:  {', '.join(sig['buy_signals'])}")
    if sig["sell_signals"]:
        print(f"    SELL: {', '.join(sig['sell_signals'])}")
    print()

print(f"{'='*60}\n")
