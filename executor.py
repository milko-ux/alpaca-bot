import math
import alpaca_trade_api as tradeapi
from datetime import datetime
from config import (
    ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL, PAPER,
    POSITION_PCT, STOP_LOSS_PCT, TAKE_PROFIT_PCT, MAX_POSITIONS,
)

api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL, api_version="v2")

MODE = "PAPER" if PAPER else "LIVE"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_portfolio_value() -> float:
    try:
        return float(api.get_account().portfolio_value)
    except Exception as e:
        print(f"[executor] FEL portfolio_value: {e}")
        return 0.0


def get_cash() -> float:
    try:
        return float(api.get_account().cash)
    except Exception as e:
        print(f"[executor] FEL cash: {e}")
        return 0.0


def get_open_positions() -> list[dict]:
    """Returnerar lista med öppna positions."""
    try:
        positions = api.list_positions()
        return [
            {
                "symbol":     p.symbol,
                "qty":        float(p.qty),
                "avg_entry":  float(p.avg_entry_price),
                "current":    float(p.current_price),
                "unrealized_pct": float(p.unrealized_plpc),
                "market_val": float(p.market_value),
            }
            for p in positions
        ]
    except Exception as e:
        print(f"[executor] FEL list_positions: {e}")
        return []


def count_open_positions() -> int:
    return len(get_open_positions())


def get_latest_price(symbol: str) -> float:
    try:
        return float(api.get_latest_trade(symbol, feed="iex").price)
    except Exception:
        try:
            return float(api.get_latest_quote(symbol, feed="iex").ask_price)
        except Exception as e:
            print(f"[executor] FEL pris {symbol}: {e}")
            return 0.0


def has_position(symbol: str) -> bool:
    try:
        api.get_position(symbol)
        return True
    except Exception:
        return False


def get_position_qty(symbol: str) -> float:
    try:
        return float(api.get_position(symbol).qty)
    except Exception:
        return 0.0


def has_pending_order(symbol: str) -> bool:
    """Returnerar True om det finns en öppen (ej fylld) order för symbolen."""
    try:
        orders = api.list_orders(status="open", symbols=[symbol])
        return len(orders) > 0
    except Exception:
        return False


def cancel_existing_orders(symbol: str) -> None:
    try:
        orders = api.list_orders(status="open", symbols=[symbol])
        for o in orders:
            api.cancel_order(o.id)
            print(f"[executor] Avbröt order {o.id} för {symbol}")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Buy
# ---------------------------------------------------------------------------

def buy(symbol: str, signal: dict) -> dict | None:
    n_open = count_open_positions()
    if n_open >= MAX_POSITIONS:
        print(f"[executor] {symbol}: MAX_POSITIONS ({MAX_POSITIONS}) nått — hoppar över.")
        return None

    portfolio = get_portfolio_value()
    cash      = get_cash()
    notional  = round(portfolio * POSITION_PCT, 2)

    if notional > cash:
        print(f"[executor] {symbol}: otillräckligt cash (${cash:.2f} < ${notional:.2f})")
        return None

    price       = get_latest_price(symbol)
    if price <= 0:
        return None
    qty         = math.floor(notional / price)
    if qty < 1:
        print(f"[executor] {symbol}: qty < 1 (${notional:.2f} / ${price:.2f}) — hoppar.")
        return None
    limit_price = round(price * 1.002, 2)   # limit 0.2% över senaste pris
    stop_price  = round(price * (1 - STOP_LOSS_PCT), 2)
    take_price  = round(price * (1 + TAKE_PROFIT_PCT), 2)

    reasons = ", ".join(signal.get("buy_signals", []))
    ts      = datetime.now().strftime("%H:%M:%S")

    print(f"\n[executor] [{MODE}] *** KÖP {symbol} ***")
    print(f"  Tid:        {ts}")
    print(f"  Pris:       ${price:.2f}  |  Limit: ${limit_price:.2f}")
    print(f"  Antal:      {qty}  (~${notional:.2f})")
    print(f"  Stop-loss:  ${stop_price:.2f}  (-{STOP_LOSS_PCT*100:.0f}%)")
    print(f"  Take-profit:${take_price:.2f}  (+{TAKE_PROFIT_PCT*100:.0f}%)")
    print(f"  Signaler:   {reasons}")

    try:
        cancel_existing_orders(symbol)

        order = api.submit_order(
            symbol=symbol,
            qty=qty,
            side="buy",
            type="limit",
            time_in_force="day",
            limit_price=str(limit_price),
            order_class="bracket",
            stop_loss={"stop_price": str(stop_price)},
            take_profit={"limit_price": str(take_price)},
        )
        print(f"  Order-ID:   {order.id}  status={order.status}")
        return {"symbol": symbol, "side": "buy", "order_id": order.id,
                "qty": qty, "limit": limit_price, "stop": stop_price, "tp": take_price}
    except Exception as e:
        print(f"[executor] FEL KÖP {symbol}: {e}")
        return None


# ---------------------------------------------------------------------------
# Sell
# ---------------------------------------------------------------------------

def sell(symbol: str, reason: str = "signal") -> dict | None:
    qty = get_position_qty(symbol)
    if qty <= 0:
        print(f"[executor] {symbol}: ingen position att sälja.")
        return None

    price       = get_latest_price(symbol)
    limit_price = round(price * 0.998, 2)   # limit 0.2% under senaste pris
    ts          = datetime.now().strftime("%H:%M:%S")

    print(f"\n[executor] [{MODE}] *** SÄLJ {symbol} ***")
    print(f"  Tid:    {ts}  |  Anledning: {reason}")
    print(f"  Pris:   ${price:.2f}  |  Limit: ${limit_price:.2f}")
    print(f"  Antal:  {qty}")

    try:
        cancel_existing_orders(symbol)

        order = api.submit_order(
            symbol=symbol,
            qty=qty,
            side="sell",
            type="limit",
            time_in_force="day",
            limit_price=str(limit_price),
        )
        print(f"  Order-ID: {order.id}  status={order.status}")
        return {"symbol": symbol, "side": "sell", "order_id": order.id, "qty": qty}
    except Exception as e:
        print(f"[executor] FEL SÄLJ {symbol}: {e}")
        return None


# ---------------------------------------------------------------------------
# Stop-loss / Take-profit check (fallback om bracket order inte triggas)
# ---------------------------------------------------------------------------

def check_stop_take(positions: list[dict]) -> None:
    for pos in positions:
        sym  = pos["symbol"]
        pct  = pos["unrealized_pct"]
        if pct <= -STOP_LOSS_PCT or pct >= TAKE_PROFIT_PCT:
            if has_pending_order(sym):
                print(f"[executor] {sym}: bracket order aktiv — hoppar fallback stop/take.")
                continue
            if pct <= -STOP_LOSS_PCT:
                print(f"[executor] {sym}: STOP-LOSS triggrad ({pct*100:.1f}%)")
                sell(sym, reason=f"stop-loss {pct*100:.1f}%")
            else:
                print(f"[executor] {sym}: TAKE-PROFIT triggrad ({pct*100:.1f}%)")
                sell(sym, reason=f"take-profit {pct*100:.1f}%")


# ---------------------------------------------------------------------------
# Execute (körs från main.py)
# ---------------------------------------------------------------------------

def execute(signal: dict) -> None:
    symbol    = signal["symbol"]
    direction = signal["direction"]

    if direction == "BUY":
        if not has_position(symbol):
            buy(symbol, signal)
        else:
            print(f"[executor] {symbol}: BUY — position finns redan, hoppar.")
    elif direction == "SELL":
        if has_position(symbol):
            reasons = ", ".join(signal.get("sell_signals", []))
            sell(symbol, reason=f"signal ({reasons})")
        else:
            print(f"[executor] {symbol}: SELL — ingen position.")
    else:
        pass   # HOLD — tyst
