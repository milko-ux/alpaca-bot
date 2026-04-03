import time
from datetime import datetime, timezone, timedelta


import config as cfg
from signals import get_signal
from executor import (
    api, execute, get_open_positions, get_portfolio_value,
    check_stop_take, MODE,
)

_last_portfolio_log = 0.0   # epoch-tid för senaste portfolio-logg


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def fetch_bars(symbol: str) -> list[dict]:
    """Hämtar ~2 månaders daglig OHLCV-data, returnerar lista av dicts (äldst först)."""
    try:
        end   = datetime.now(timezone.utc)
        start = end - timedelta(days=90)
        df = api.get_bars(
            symbol, "1Day",
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            limit=cfg.BARS_NEEDED,
            feed="iex",
        ).df
        if df.empty:
            return []
        return [
            {
                "open":   float(row["open"]),
                "high":   float(row["high"]),
                "low":    float(row["low"]),
                "close":  float(row["close"]),
                "volume": float(row["volume"]),
            }
            for _, row in df.iterrows()
        ]
    except Exception as e:
        print(f"[main] FEL bars {symbol}: {e}")
        return []


# ---------------------------------------------------------------------------
# Market status
# ---------------------------------------------------------------------------

def is_market_open() -> bool:
    try:
        return api.get_clock().is_open
    except Exception:
        return False


def next_open_in_seconds() -> int:
    """Returnerar sekunder till nästa marknadsöppning (eller 0 om öppen)."""
    try:
        clock = api.get_clock()
        if clock.is_open:
            return 0
        next_open = clock.next_open
        # next_open är en sträng eller datetime beroende på SDK-version
        if isinstance(next_open, str):
            next_open = datetime.fromisoformat(next_open.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return max(0, int((next_open - now).total_seconds()))
    except Exception:
        return cfg.LOOP_INTERVAL_SEC


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log_portfolio() -> None:
    global _last_portfolio_log
    now = time.time()
    if now - _last_portfolio_log < 3600:
        return
    _last_portfolio_log = now
    val       = get_portfolio_value()
    positions = get_open_positions()
    ts        = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*55}")
    print(f"[portfolio] {ts}  |  Värde: ${val:,.2f}")
    if positions:
        for p in positions:
            sign  = "+" if p["unrealized_pct"] >= 0 else ""
            print(f"  {p['symbol']:5s}  qty={p['qty']}  entry=${p['avg_entry']:.2f}  "
                  f"nu=${p['current']:.2f}  P/L={sign}{p['unrealized_pct']*100:.1f}%  "
                  f"val=${p['market_val']:,.2f}")
    else:
        print("  (inga öppna positions)")
    print(f"{'='*55}\n")


def log_positions_summary(positions: list[dict]) -> None:
    n = len(positions)
    print(f"[main] Öppna positions: {n}/{cfg.MAX_POSITIONS}")
    for p in positions:
        sign = "+" if p["unrealized_pct"] >= 0 else ""
        print(f"  {p['symbol']:5s}  {sign}{p['unrealized_pct']*100:.1f}%  "
              f"entry=${p['avg_entry']:.2f}  nu=${p['current']:.2f}")


# ---------------------------------------------------------------------------
# Huvud-loop
# ---------------------------------------------------------------------------

def run_loop() -> None:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*55}")
    print(f"[main] Loop — {now_str}  [{MODE}]")
    print(f"{'='*55}")

    if not is_market_open():
        secs = next_open_in_seconds()
        print(f"[main] Marknaden är stängd — nästa öppning om ~{secs//3600}h {(secs%3600)//60}m")
        return

    # Logga portfolio varje timme
    log_portfolio()

    # Hämta öppna positions och kolla stop/take (fallback)
    positions = get_open_positions()
    log_positions_summary(positions)
    check_stop_take(positions)

    # Kör signaler för varje symbol
    for symbol in cfg.SYMBOLS:
        bars = fetch_bars(symbol)
        if not bars:
            print(f"[main] {symbol}: ingen data.")
            continue

        signal = get_signal(symbol, bars, cfg)

        # Logga indikatorer
        rsi_s   = f"RSI={signal['rsi']:.1f}" if signal["rsi"] else "RSI=N/A"
        macd_s  = f"MACD={'bullish' if signal['macd'].get('bullish') else 'bearish'}"
        bb_pct  = signal["bb"].get("pct", 0) * 100
        pat_s   = f"  [{signal['pattern']}]" if signal["pattern"] else ""
        buy_s   = signal["buy_signals"]
        sell_s  = signal["sell_signals"]

        print(
            f"[main] {symbol:5s}  {rsi_s:12s}  {macd_s:14s}  BB={bb_pct:5.1f}%  "
            f"score={signal['score']:+d}  → {signal['direction']}{pat_s}"
        )
        if buy_s:
            print(f"         BUY-signaler:  {', '.join(buy_s)}")
        if sell_s:
            print(f"         SELL-signaler: {', '.join(sell_s)}")

        execute(signal)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    val = get_portfolio_value()
    print(f"[main] Alpaca-bot startar [{MODE}]")
    print(f"[main] Portfolio: ${val:,.2f}")
    print(f"[main] Symboler:  {cfg.SYMBOLS}")
    print(f"[main] Per trade: {cfg.POSITION_PCT*100:.0f}% av portfolio "
          f"(~${val*cfg.POSITION_PCT:,.0f})")
    print(f"[main] Stop-loss: -{cfg.STOP_LOSS_PCT*100:.0f}%  "
          f"Take-profit: +{cfg.TAKE_PROFIT_PCT*100:.0f}%")
    print(f"[main] Max positions: {cfg.MAX_POSITIONS}  "
          f"Min signaler: {cfg.MIN_SIGNALS}/3")
    print(f"[main] Intervall: {cfg.LOOP_INTERVAL_SEC}s\n")

    # Logga portfolio direkt vid start
    _last_portfolio_log = 0.0
    log_portfolio()

    while True:
        run_loop()
        print(f"[main] Nästa körning om {cfg.LOOP_INTERVAL_SEC}s.")
        time.sleep(cfg.LOOP_INTERVAL_SEC)
