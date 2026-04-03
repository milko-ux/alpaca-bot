"""
patterns.py — Deterministiska candlestick-mönster baserade på regler från KB.

Källor:
- CandleandBreakoutPatternCheatSheetGuide.pdf
- all-candlestick-patterns-pdf.pdf
- Identifying-Chart-Patterns.pdf
- Murphy_OCR.txt (Technical Analysis of Financial Markets)

Alla funktioner tar en lista av OHLCV-dicts:
    [{"open": f, "high": f, "low": f, "close": f, "volume": f}, ...]

och returnerar bool. Senaste candle i listan är den aktuella.
Kommentarer anger de exakta numeriska kriterierna från böckerna.
"""


# ---------------------------------------------------------------------------
# Hjälpfunktioner
# ---------------------------------------------------------------------------

def _body(c: dict) -> float:
    return abs(c["close"] - c["open"])

def _span(c: dict) -> float:
    return c["high"] - c["low"]

def _upper_shadow(c: dict) -> float:
    return c["high"] - max(c["open"], c["close"])

def _lower_shadow(c: dict) -> float:
    return min(c["open"], c["close"]) - c["low"]

def _is_bullish(c: dict) -> bool:
    return c["close"] > c["open"]

def _is_bearish(c: dict) -> bool:
    return c["close"] < c["open"]

def _body_mid(c: dict) -> float:
    return (c["open"] + c["close"]) / 2


# ---------------------------------------------------------------------------
# 1. Hammer — Bullish Reversal
# ---------------------------------------------------------------------------

def detect_hammer(candles: list[dict]) -> bool:
    """
    Regler (all-candlestick-patterns-pdf.pdf):
    - Litet body: body / span < 0.35
    - Lång nedre skugga: lower_shadow / span > 0.55
    - Kort övre skugga: upper_shadow / span < 0.15
    - Förekommer efter nedtrend (senaste 3 closes sjunker)
    """
    if not candles or len(candles) < 4:
        return False
    c = candles[-2]  # senast stängda candle
    sp = _span(c)
    if sp < 1e-8:
        return False
    body_ratio  = _body(c) / sp
    lower_ratio = _lower_shadow(c) / sp
    upper_ratio = _upper_shadow(c) / sp
    shape_ok = body_ratio < 0.35 and lower_ratio > 0.55 and upper_ratio < 0.15
    # Nedtrend: de tre föregående stänger sjunker
    in_downtrend = candles[-4]["close"] > candles[-3]["close"] > candles[-2]["close"]
    return shape_ok and in_downtrend


# ---------------------------------------------------------------------------
# 2. Shooting Star — Bearish Reversal
# ---------------------------------------------------------------------------

def detect_shooting_star(candles: list[dict]) -> bool:
    """
    Regler (Murphy + all-candlestick-patterns-pdf.pdf):
    - Litet body: body / span < 0.35
    - Lång övre skugga: upper_shadow / span > 0.55
    - Kort nedre skugga: lower_shadow / span < 0.15
    - Förekommer efter upptrend (senaste 3 closes stiger)
    """
    if not candles or len(candles) < 4:
        return False
    c = candles[-2]
    sp = _span(c)
    if sp < 1e-8:
        return False
    body_ratio  = _body(c) / sp
    upper_ratio = _upper_shadow(c) / sp
    lower_ratio = _lower_shadow(c) / sp
    shape_ok = body_ratio < 0.35 and upper_ratio > 0.55 and lower_ratio < 0.15
    in_uptrend = candles[-4]["close"] < candles[-3]["close"] < candles[-2]["close"]
    return shape_ok and in_uptrend


# ---------------------------------------------------------------------------
# 3. Bullish Engulfing — Bullish Reversal
# ---------------------------------------------------------------------------

def detect_bullish_engulfing(candles: list[dict]) -> bool:
    """
    Regler (all-candlestick-patterns-pdf.pdf):
    - Candle N-1: bearish (close < open)
    - Candle N:   bullish (close > open)
    - Candle N body omsluter helt candle N-1 body:
        N.open  < N-1.close  OCH  N.close > N-1.open
    - N body minst 1.1× N-1 body (tydlig omslutning)
    """
    if not candles or len(candles) < 2:
        return False
    prev = candles[-2]
    curr = candles[-1]
    if not (_is_bearish(prev) and _is_bullish(curr)):
        return False
    engulfs = curr["open"] < prev["close"] and curr["close"] > prev["open"]
    big_enough = _body(curr) >= _body(prev) * 1.1
    return engulfs and big_enough


# ---------------------------------------------------------------------------
# 4. Bearish Engulfing — Bearish Reversal
# ---------------------------------------------------------------------------

def detect_bearish_engulfing(candles: list[dict]) -> bool:
    """
    Regler (all-candlestick-patterns-pdf.pdf):
    - Candle N-1: bullish
    - Candle N:   bearish
    - N.open > N-1.close  OCH  N.close < N-1.open
    - N body minst 1.1× N-1 body
    """
    if not candles or len(candles) < 2:
        return False
    prev = candles[-2]
    curr = candles[-1]
    if not (_is_bullish(prev) and _is_bearish(curr)):
        return False
    engulfs = curr["open"] > prev["close"] and curr["close"] < prev["open"]
    big_enough = _body(curr) >= _body(prev) * 1.1
    return engulfs and big_enough


# ---------------------------------------------------------------------------
# 5. Morning Star — Bullish Reversal (3 candles)
# ---------------------------------------------------------------------------

def detect_morning_star(candles: list[dict]) -> bool:
    """
    Regler (all-candlestick-patterns-pdf.pdf, reliability=High):
    - Candle N-2: stor bearish candle  (body > span * 0.5)
    - Candle N-1: litet body (indecision), body < N-2 body * 0.4
    - Candle N:   bullish, stänger ovanför mitten av N-2 body
    - N-1 stänger under lows av N-2 (gap ner, men accepterar overlap på 1-min)
    """
    if not candles or len(candles) < 3:
        return False
    c1, c2, c3 = candles[-3], candles[-2], candles[-1]
    big_bearish   = _is_bearish(c1) and _body(c1) > _span(c1) * 0.5
    small_middle  = _body(c2) < _body(c1) * 0.4
    bullish_close = _is_bullish(c3) and c3["close"] > _body_mid(c1)
    return big_bearish and small_middle and bullish_close


# ---------------------------------------------------------------------------
# 6. Evening Star — Bearish Reversal (3 candles)
# ---------------------------------------------------------------------------

def detect_evening_star(candles: list[dict]) -> bool:
    """
    Regler (all-candlestick-patterns-pdf.pdf, reliability=High):
    - Candle N-2: stor bullish  (body > span * 0.5)
    - Candle N-1: litet body,   body < N-2 body * 0.4
    - Candle N:   bearish, stänger under mitten av N-2 body
    """
    if not candles or len(candles) < 3:
        return False
    c1, c2, c3 = candles[-3], candles[-2], candles[-1]
    big_bullish   = _is_bullish(c1) and _body(c1) > _span(c1) * 0.5
    small_middle  = _body(c2) < _body(c1) * 0.4
    bearish_close = _is_bearish(c3) and c3["close"] < _body_mid(c1)
    return big_bullish and small_middle and bearish_close


# ---------------------------------------------------------------------------
# 7. Three White Soldiers — Bullish Continuation/Reversal
# ---------------------------------------------------------------------------

def detect_three_white_soldiers(candles: list[dict]) -> bool:
    """
    Regler (all-candlestick-patterns-pdf.pdf, reliability=High):
    - 3 consecutiva bullish candles med progressivt högre closes
    - Varje candle öppnar inom föregående bodys range
    - Varje body > span * 0.5 (starka candles utan långa skuggor)
    - Candle N.close > N-1.close > N-2.close
    """
    if not candles or len(candles) < 3:
        return False
    c1, c2, c3 = candles[-3], candles[-2], candles[-1]
    all_bullish = _is_bullish(c1) and _is_bullish(c2) and _is_bullish(c3)
    rising_closes = c3["close"] > c2["close"] > c1["close"]
    opens_in_body = (
        c1["open"] < c2["open"] < c1["close"] and
        c2["open"] < c3["open"] < c2["close"]
    )
    strong_bodies = (
        _body(c1) > _span(c1) * 0.5 and
        _body(c2) > _span(c2) * 0.5 and
        _body(c3) > _span(c3) * 0.5
    )
    return all_bullish and rising_closes and opens_in_body and strong_bodies


# ---------------------------------------------------------------------------
# 8. Dark Cloud Cover — Bearish Reversal (2 candles)
# ---------------------------------------------------------------------------

def detect_dark_cloud_cover(candles: list[dict]) -> bool:
    """
    Regler (anpassad för 5-min data utan gap-krav):
    - Candle N-1: bullish
    - Candle N:   bearish
    - N öppnar inom N-1 body (open < N-1 close, open > N-1 open)
    - N stänger under mitten av N-1 body (close < N-1 body_mid)
    - N stänger ovan N-1 open (ingen full engulfing)
    """
    if not candles or len(candles) < 2:
        return False
    prev = candles[-2]
    curr = candles[-1]
    if not (_is_bullish(prev) and _is_bearish(curr)):
        return False
    opens_within_body = prev["open"] < curr["open"] < prev["close"]
    closes_below_mid  = curr["close"] < _body_mid(prev)
    closes_above_open = curr["close"] > prev["open"]
    return opens_within_body and closes_below_mid and closes_above_open


# ---------------------------------------------------------------------------
# 9. Piercing Line — Bullish Reversal (2 candles)
# ---------------------------------------------------------------------------

def detect_piercing_line(candles: list[dict]) -> bool:
    """
    Regler (anpassad för 5-min data utan gap-krav):
    - Candle N-1: bearish
    - Candle N:   bullish
    - N öppnar inom N-1 body (open > N-1 close, open < N-1 open)
    - N stänger ovanför mitten av N-1 body (close > N-1 body_mid)
    - N stänger under N-1 open (ingen full engulfing)
    """
    if not candles or len(candles) < 2:
        return False
    prev = candles[-2]
    curr = candles[-1]
    if not (_is_bearish(prev) and _is_bullish(curr)):
        return False
    opens_within_body = prev["close"] < curr["open"] < prev["open"]
    closes_above_mid  = curr["close"] > _body_mid(prev)
    closes_below_open = curr["close"] < prev["open"]
    return opens_within_body and closes_above_mid and closes_below_open


# ---------------------------------------------------------------------------
# 10. Tweezer Top — Bearish Reversal
# ---------------------------------------------------------------------------

def detect_tweezer_top(candles: list[dict]) -> bool:
    """
    Regler (all-candlestick-patterns-pdf.pdf, reliability=Medium):
    - 2 candles med matchande highs (inom 0.05% tolerans)
    - Candle N-1: bullish (upptrend bekräftad)
    - Candle N:   bearish (avvisning av höga nivån)
    - Matchande highs indikerar stark resistance
    """
    if not candles or len(candles) < 2:
        return False
    prev = candles[-2]
    curr = candles[-1]
    if not (_is_bullish(prev) and _is_bearish(curr)):
        return False
    high_avg = (prev["high"] + curr["high"]) / 2
    if high_avg < 1e-8:
        return False
    matching_highs = abs(prev["high"] - curr["high"]) / high_avg < 0.0005
    return matching_highs


# ---------------------------------------------------------------------------
# 11. Tweezer Bottom — Bullish Reversal
# ---------------------------------------------------------------------------

def detect_tweezer_bottom(candles: list[dict]) -> bool:
    """
    Regler (all-candlestick-patterns-pdf.pdf, reliability=Medium):
    - 2 candles med matchande lows (inom 0.05% tolerans)
    - Candle N-1: bearish (nedtrend bekräftad)
    - Candle N:   bullish (avvisning av låga nivån)
    - Matchande lows indikerar stark support
    """
    if not candles or len(candles) < 2:
        return False
    prev = candles[-2]
    curr = candles[-1]
    if not (_is_bearish(prev) and _is_bullish(curr)):
        return False
    low_avg = (prev["low"] + curr["low"]) / 2
    if low_avg < 1e-8:
        return False
    matching_lows = abs(prev["low"] - curr["low"]) / low_avg < 0.0005
    return matching_lows


# ---------------------------------------------------------------------------
# Samlad detektering
# ---------------------------------------------------------------------------

BULLISH_PATTERNS = [
    ("Hammer",             detect_hammer),
    ("Bullish Engulfing",  detect_bullish_engulfing),
    ("Morning Star",       detect_morning_star),
    ("Three White Soldiers", detect_three_white_soldiers),
    ("Piercing Line",      detect_piercing_line),
    ("Tweezer Bottom",     detect_tweezer_bottom),
]

BEARISH_PATTERNS = [
    ("Shooting Star",      detect_shooting_star),
    ("Bearish Engulfing",  detect_bearish_engulfing),
    ("Evening Star",       detect_evening_star),
    ("Dark Cloud Cover",   detect_dark_cloud_cover),
    ("Tweezer Top",        detect_tweezer_top),
]


def detect_all(candles: list[dict]) -> dict:
    """
    Kör alla mönster mot candle-listan.
    Returnerar {"bullish": [namn, ...], "bearish": [namn, ...]}.
    """
    bullish = [name for name, fn in BULLISH_PATTERNS if fn(candles)]
    bearish = [name for name, fn in BEARISH_PATTERNS if fn(candles)]
    return {"bullish": bullish, "bearish": bearish}
