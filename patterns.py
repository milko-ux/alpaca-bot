"""
patterns.py — Deterministiska candlestick-mönster baserade på regler från KB.

VIKTIGT: candles[-1] = dagens pågående (ofullständiga) bar.
         Alla mönster arbetar med candles[-2] som senast STÄNGDA bar.
"""


def _body(c): return abs(c["close"] - c["open"])
def _span(c): return c["high"] - c["low"]
def _upper_shadow(c): return c["high"] - max(c["open"], c["close"])
def _lower_shadow(c): return min(c["open"], c["close"]) - c["low"]
def _is_bullish(c): return c["close"] > c["open"]
def _is_bearish(c): return c["close"] < c["open"]
def _body_mid(c): return (c["open"] + c["close"]) / 2


def detect_hammer(candles):
    if len(candles) < 4: return False
    c = candles[-2]
    sp = _span(c)
    if sp < 1e-8: return False
    shape_ok = (_body(c)/sp < 0.35 and _lower_shadow(c)/sp > 0.55 and _upper_shadow(c)/sp < 0.15)
    in_downtrend = candles[-4]["close"] > candles[-3]["close"] > candles[-2]["close"]
    return shape_ok and in_downtrend


def detect_shooting_star(candles):
    if len(candles) < 4: return False
    c = candles[-2]
    sp = _span(c)
    if sp < 1e-8: return False
    shape_ok = (_body(c)/sp < 0.35 and _upper_shadow(c)/sp > 0.55 and _lower_shadow(c)/sp < 0.15)
    in_uptrend = candles[-4]["close"] < candles[-3]["close"] < candles[-2]["close"]
    return shape_ok and in_uptrend


def detect_bullish_engulfing(candles):
    if len(candles) < 4: return False
    prev = candles[-3]
    curr = candles[-2]
    if not (_is_bearish(prev) and _is_bullish(curr)): return False
    engulfs = curr["open"] < prev["close"] and curr["close"] > prev["open"]
    big_enough = _body(curr) >= _body(prev) * 1.1
    return engulfs and big_enough


def detect_bearish_engulfing(candles):
    if len(candles) < 4: return False
    prev = candles[-3]
    curr = candles[-2]
    if not (_is_bullish(prev) and _is_bearish(curr)): return False
    engulfs = curr["open"] > prev["close"] and curr["close"] < prev["open"]
    big_enough = _body(curr) >= _body(prev) * 1.1
    return engulfs and big_enough


def detect_morning_star(candles):
    if len(candles) < 5: return False
    c1, c2, c3 = candles[-4], candles[-3], candles[-2]
    big_bearish  = _is_bearish(c1) and _body(c1) > _span(c1) * 0.5
    small_middle = _body(c2) < _body(c1) * 0.4
    bullish_close = _is_bullish(c3) and c3["close"] > _body_mid(c1)
    return big_bearish and small_middle and bullish_close


def detect_evening_star(candles):
    if len(candles) < 5: return False
    c1, c2, c3 = candles[-4], candles[-3], candles[-2]
    big_bullish  = _is_bullish(c1) and _body(c1) > _span(c1) * 0.5
    small_middle = _body(c2) < _body(c1) * 0.4
    bearish_close = _is_bearish(c3) and c3["close"] < _body_mid(c1)
    return big_bullish and small_middle and bearish_close


def detect_three_white_soldiers(candles):
    if len(candles) < 5: return False
    c1, c2, c3 = candles[-4], candles[-3], candles[-2]
    all_bullish   = _is_bullish(c1) and _is_bullish(c2) and _is_bullish(c3)
    rising_closes = c3["close"] > c2["close"] > c1["close"]
    opens_in_body = (c1["open"] < c2["open"] < c1["close"] and
                     c2["open"] < c3["open"] < c2["close"])
    strong_bodies = (_body(c1) > _span(c1)*0.5 and
                     _body(c2) > _span(c2)*0.5 and
                     _body(c3) > _span(c3)*0.5)
    return all_bullish and rising_closes and opens_in_body and strong_bodies


def detect_dark_cloud_cover(candles):
    if len(candles) < 4: return False
    prev = candles[-3]
    curr = candles[-2]
    if not (_is_bullish(prev) and _is_bearish(curr)): return False
    opens_within = prev["open"] < curr["open"] < prev["close"]
    closes_below_mid = curr["close"] < _body_mid(prev)
    closes_above_open = curr["close"] > prev["open"]
    return opens_within and closes_below_mid and closes_above_open


def detect_piercing_line(candles):
    if len(candles) < 4: return False
    prev = candles[-3]
    curr = candles[-2]
    if not (_is_bearish(prev) and _is_bullish(curr)): return False
    opens_within = prev["close"] < curr["open"] < prev["open"]
    closes_above_mid = curr["close"] > _body_mid(prev)
    closes_below_open = curr["close"] < prev["open"]
    return opens_within and closes_above_mid and closes_below_open


def detect_tweezer_top(candles):
    if len(candles) < 4: return False
    prev = candles[-3]
    curr = candles[-2]
    if not (_is_bullish(prev) and _is_bearish(curr)): return False
    high_avg = (prev["high"] + curr["high"]) / 2
    if high_avg < 1e-8: return False
    return abs(prev["high"] - curr["high"]) / high_avg < 0.002


def detect_tweezer_bottom(candles):
    if len(candles) < 4: return False
    prev = candles[-3]
    curr = candles[-2]
    if not (_is_bearish(prev) and _is_bullish(curr)): return False
    low_avg = (prev["low"] + curr["low"]) / 2
    if low_avg < 1e-8: return False
    return abs(prev["low"] - curr["low"]) / low_avg < 0.002


BULLISH_PATTERNS = [
    ("Hammer",               detect_hammer),
    ("Bullish Engulfing",    detect_bullish_engulfing),
    ("Morning Star",         detect_morning_star),
    ("Three White Soldiers", detect_three_white_soldiers),
    ("Piercing Line",        detect_piercing_line),
    ("Tweezer Bottom",       detect_tweezer_bottom),
]

BEARISH_PATTERNS = [
    ("Shooting Star",     detect_shooting_star),
    ("Bearish Engulfing", detect_bearish_engulfing),
    ("Evening Star",      detect_evening_star),
    ("Dark Cloud Cover",  detect_dark_cloud_cover),
    ("Tweezer Top",       detect_tweezer_top),
]


def detect_all(candles):
    bullish = [name for name, fn in BULLISH_PATTERNS if fn(candles)]
    bearish = [name for name, fn in BEARISH_PATTERNS if fn(candles)]
    return {"bullish": bullish, "bearish": bearish}
