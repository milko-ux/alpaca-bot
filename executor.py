import alpaca_trade_api as tradeapi
from config import (
    ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL,
    DRY_RUN, TRADE_AMOUNT_USD,
)

api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL, api_version="v2")


def get_position(symbol: str) -> float:
    """Returnerar nuvarande antal aktier vi äger (0 om ingen position)."""
    try:
        pos = api.get_position(symbol)
        return float(pos.qty)
    except Exception:
        return 0.0


def get_price(symbol: str) -> float:
    """Senaste handelspris."""
    try:
        trade = api.get_latest_trade(symbol)
        return float(trade.price)
    except Exception:
        quote = api.get_latest_quote(symbol)
        return float(quote.ask_price)


def buy(symbol: str) -> dict | None:
    """Köper $TRADE_AMOUNT_USD av symbolen (fractional shares)."""
    mode = "DRY-RUN" if DRY_RUN else "LIVE"
    try:
        if DRY_RUN:
            price = get_price(symbol)
            qty   = round(TRADE_AMOUNT_USD / price, 6)
            print(f"[executor] [{mode}] KÖP {symbol} ~${TRADE_AMOUNT_USD:.2f} @ ${price:.2f} ({qty} aktier)")
            return {"symbol": symbol, "side": "buy", "notional": TRADE_AMOUNT_USD, "dry_run": True}

        order = api.submit_order(
            symbol=symbol,
            notional=TRADE_AMOUNT_USD,
            side="buy",
            type="market",
            time_in_force="day",
        )
        print(f"[executor] [{mode}] KÖP {symbol} ${TRADE_AMOUNT_USD:.2f} — order {order.id}")
        return {"symbol": symbol, "side": "buy", "order_id": order.id}
    except Exception as e:
        print(f"[executor] FEL vid KÖP {symbol}: {e}")
        return None


def sell(symbol: str) -> dict | None:
    """Säljer hela positionen i symbolen."""
    mode = "DRY-RUN" if DRY_RUN else "LIVE"
    qty  = get_position(symbol)
    if qty <= 0:
        print(f"[executor] {symbol}: ingen position att sälja.")
        return None
    try:
        if DRY_RUN:
            price = get_price(symbol)
            print(f"[executor] [{mode}] SÄLJ {symbol} {qty} aktier @ ${price:.2f}")
            return {"symbol": symbol, "side": "sell", "qty": qty, "dry_run": True}

        order = api.submit_order(
            symbol=symbol,
            qty=qty,
            side="sell",
            type="market",
            time_in_force="day",
        )
        print(f"[executor] [{mode}] SÄLJ {symbol} {qty} aktier — order {order.id}")
        return {"symbol": symbol, "side": "sell", "order_id": order.id}
    except Exception as e:
        print(f"[executor] FEL vid SÄLJ {symbol}: {e}")
        return None


def execute(signal: dict) -> None:
    """Kör köp/sälj baserat på signal från signals.py."""
    symbol    = signal["symbol"]
    direction = signal["direction"]
    has_pos   = get_position(symbol) > 0

    if direction == "BUY" and not has_pos:
        buy(symbol)
    elif direction == "SELL" and has_pos:
        sell(symbol)
    else:
        print(f"[executor] {symbol}: {direction} — ingen åtgärd (position={has_pos})")
