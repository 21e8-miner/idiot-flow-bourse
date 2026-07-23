#!/usr/bin/env python3
"""
Core engine for the RJ Idiot Flow scanner.

Combines:
  1) Multi-horizon board-path projection (lab)
  2) Pine RJ_24H_Roll_Off_Adaptive_v2 classic + adaptive filters

Pine core (1h bars, 24h window):
  currentWindowReturn  = close / close[24] - 1
  flatNextWindowReturn = close / close[23] - 1
  knownRollDelta       = flatNext - current
  outgoingReturn       = close[23] / close[24] - 1

  Long  if outgoing is largest RED  in window and knownRollDelta > 0
  Short if outgoing is largest GREEN in window and knownRollDelta < 0

Adaptive: shock z, edge z, attention percentile, RVOL, trend veto, optional zero-cross.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


MAGNETS = (0.0, 5.0, -5.0, 10.0, -10.0, 15.0, -15.0, 20.0, -20.0)
EPS = 1e-12


@dataclass
class Candle:
    open_time: int
    open: float
    high: float
    low: float
    close: float
    quote_volume: float


@dataclass
class AdaptiveConfig:
    """Defaults mirror RJ_24H_Roll_Off_Adaptive_v2.pine."""

    roll_hours: int = 24
    vol_lookback_hours: int = 168
    attention_lookback_hours: int = 720
    trend_hours: int = 6
    rvol_lookback_hours: int = 24

    min_shock_pct: float = 0.75
    min_shock_z: float = 1.50
    min_roll_pct: float = 0.50
    min_edge_z: float = 0.75
    min_attention_rank: float = 60.0
    min_rvol: float = 0.60
    counter_trend_cap_pct: float = 3.0

    use_attention: bool = True
    use_rvol: bool = True
    use_trend_veto: bool = True
    require_zero_cross: bool = False
    require_window_extreme: bool = True  # classic article / pine gate

    # Path / lab
    horizon: int = 12
    min_abs_cliff: float = 0.35

    # Mode:
    #   classic  = only adaptive READY (strict tradeable)
    #   adaptive = classic raw setups (READY + FILTERED OUT) — Pine dashboard
    #   explore  = also mechanical path-only drifts
    mode: str = "adaptive"


@dataclass
class PathPoint:
    hours_ahead: int
    displayed_24h_pct: float
    ref_price: float
    step_drift_pp: float


@dataclass
class Idea:
    symbol: str
    venue: str
    side: str
    price: float

    next_drift_pp: float
    roll_move_pct: float
    roll_volume: float
    roll_open_time: str

    path: list[PathPoint]
    cliff_pp: float
    cliff_hour: int
    path_end_drift_pp: float
    current_24h_pct: float
    projected_24h_at_cliff: float
    flat_next_24h_pct: float
    known_roll_delta_pp: float

    # Pine adaptive diagnostics
    outgoing_return_pct: float
    outgoing_z: float
    roll_edge_z: float
    attention_rank: float
    rvol: float
    recent_trend_pct: float
    strength_pine: float
    is_window_extreme: bool
    classic_raw: bool
    adaptive_pass: bool
    zero_cross: bool
    setup_state: str  # LONG READY | SHORT READY | FILTERED OUT | PATH ONLY | WAIT

    score: float
    liquidity_score: float
    magnet_score: float
    clean_score: float
    freshness_score: float
    cliff_score: float

    recent_1h_pct: float
    recent_4h_pct: float
    already_moved_with_flow: bool
    reason: str
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_ret(a: float, b: float) -> float:
    if b == 0:
        return 0.0
    return a / b - 1.0


def _safe_pct(a: float, b: float) -> float:
    return _safe_ret(a, b) * 100.0


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _stdev(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    try:
        return statistics.stdev(xs)
    except statistics.StatisticsError:
        return 0.0


def _percentrank(series: list[float], value: float) -> float:
    """Pine-like percentrank: % of lookback values <= value (0-100)."""
    if not series:
        return 50.0
    n = len(series)
    le = sum(1 for x in series if x <= value)
    return 100.0 * le / n


def bar_returns(closes: list[float]) -> list[float]:
    """ret[i] = close[i]/close[i-1]-1; ret[0]=nan-like 0 unused."""
    out = [0.0]
    for i in range(1, len(closes)):
        out.append(_safe_ret(closes[i], closes[i - 1]))
    return out


def project_24h_path(
    closes: list[float],
    price: float,
    roll_hours: int = 24,
    horizon: int = 12,
) -> list[PathPoint]:
    """
    Flat-price path of displayed roll-window return.
    At +h hours, ref = close from (roll_hours - h) bars ago.
    """
    n = len(closes)
    if n < roll_hours + 2:
        return []

    path: list[PathPoint] = []
    prev: float | None = None
    # index of "now"
    i_now = n - 1
    for h in range(0, horizon + 1):
        # bars ago for reference
        ago = roll_hours - h
        if ago < 0:
            break
        idx = i_now - ago
        if idx < 0:
            continue
        ref = closes[idx]
        if ref <= 0:
            continue
        disp = _safe_pct(price, ref)
        step = 0.0 if prev is None else disp - prev
        path.append(
            PathPoint(
                hours_ahead=h,
                displayed_24h_pct=round(disp, 4),
                ref_price=ref,
                step_drift_pp=round(step, 4),
            )
        )
        prev = disp
    return path


def magnet_attraction(path: list[PathPoint], side: str) -> tuple[float, list[str]]:
    if len(path) < 2:
        return 0.0, []

    tags: list[str] = []
    hits: list[float] = []
    start = path[0].displayed_24h_pct
    end = path[-1].displayed_24h_pct
    series = [p.displayed_24h_pct for p in path]

    direction_ok = (end > start and side == "LONG") or (end < start and side == "SHORT")
    if not direction_ok:
        return 0.0, tags

    for m in MAGNETS:
        crossed = False
        for a, b in zip(series, series[1:]):
            if (a - m) * (b - m) <= 0 and abs(a - b) > 1e-9:
                crossed = True
                break
        if not crossed and abs(end - m) < abs(start - m) - 0.75:
            crossed = True
        if not crossed:
            continue
        weight = 1.5 if m == 0.0 else 1.0 / (1.0 + abs(m) / 12.0)
        hits.append(weight)
        label = f"magnet {m:+.0f}%"
        if label not in tags:
            tags.append(label)

    score = 0.0
    decay = 1.0
    for w in sorted(hits, reverse=True):
        score += 9.0 * w * decay
        decay *= 0.5

    if start * end < 0:
        score += 10.0
        tags.append("sign-flip")

    return _clamp(score, 0, 22), tags


def liquidity_score(vol: float) -> float:
    if vol <= 0:
        return 0.0
    return _clamp(math.log10(vol + 1) * 6.5 - 10, 0, 35)


def freshness_score(
    side: str,
    recent_1h: float,
    recent_4h: float,
    current_24h: float,
) -> tuple[float, bool, list[str]]:
    tags: list[str] = []
    already = False

    if side == "LONG":
        pressure = max(0.0, recent_1h) + 0.5 * max(0.0, recent_4h)
        if recent_4h > 3.0 or recent_1h > 1.5:
            already = True
            tags.append("already-bid")
        bonus = _clamp(-recent_4h * 1.2, 0, 12)
        penalty = _clamp(pressure * 2.5, 0, 25)
        if current_24h < -25:
            penalty += 8
            tags.append("deep-red-board")
    else:
        pressure = max(0.0, -recent_1h) + 0.5 * max(0.0, -recent_4h)
        if recent_4h < -3.0 or recent_1h < -1.5:
            already = True
            tags.append("already-offered")
        bonus = _clamp(recent_4h * 1.2, 0, 12)
        penalty = _clamp(pressure * 2.5, 0, 25)
        if current_24h > 40:
            tags.append("mania-board")
            bonus += 4

    return _clamp(20 + bonus - penalty, 0, 35), already, tags


def cliff_metrics(path: list[PathPoint]) -> tuple[float, int, float]:
    if len(path) < 2:
        return 0.0, 0, 0.0
    best_i = 1
    best_abs = 0.0
    for i, p in enumerate(path[1:], start=1):
        a = abs(p.step_drift_pp)
        if a > best_abs:
            best_abs = a
            best_i = i
    return path[best_i].step_drift_pp, path[best_i].hours_ahead, best_abs


def pine_strength(outgoing_z: float, roll_edge_z: float, attention_rank: float) -> float:
    """0-100 strengthScore from the Pine script."""
    return 100.0 * min(
        1.0,
        0.40 * min(max(outgoing_z, 0.0) / 4.0, 1.0)
        + 0.40 * min(max(roll_edge_z, 0.0) / 3.0, 1.0)
        + 0.20 * max(attention_rank, 0.0) / 100.0,
    )


def compute_pine_metrics(
    candles: list[Candle],
    cfg: AdaptiveConfig,
) -> dict[str, Any] | None:
    """
    Pine-faithful roll-off metrics at the latest bar.
    Requires enough history for vol + attention lookbacks when those filters on.
    """
    roll = cfg.roll_hours
    n = len(candles)
    need = roll + 2
    if cfg.use_attention:
        need = max(need, cfg.attention_lookback_hours + roll + 2)
    need = max(need, cfg.vol_lookback_hours + 2)
    if n < max(need, roll + 30):
        # still try with shorter attention if we have roll window
        if n < roll + 30:
            return None

    closes = [c.close for c in candles]
    vols = [c.quote_volume for c in candles]
    rets = bar_returns(closes)
    i = n - 1  # now

    # --- known roll-off (Pine) ---
    c_now = closes[i]
    c_roll = closes[i - roll]          # close[24]
    c_out = closes[i - (roll - 1)]     # close[23]
    if c_roll <= 0 or c_out <= 0 or c_now <= 0:
        return None

    current_wr = _safe_ret(c_now, c_roll)
    flat_next = _safe_ret(c_now, c_out)
    known_delta = flat_next - current_wr
    outgoing_ret = _safe_ret(c_out, c_roll)  # barReturn[23]

    # Window bar returns currently inside the display window: rets[i-23 .. i]
    # oldest = rets[i-(roll-1)] = outgoing
    w0 = i - (roll - 1)
    w1 = i
    if w0 < 1:
        return None
    window_rets = rets[w0 : w1 + 1]
    if len(window_rets) < roll:
        return None

    wmax = max(window_rets)
    wmin = min(window_rets)
    is_largest_green = outgoing_ret > 0 and outgoing_ret >= wmax - EPS
    is_largest_red = outgoing_ret < 0 and outgoing_ret <= wmin + EPS
    is_extreme = is_largest_green or is_largest_red

    # --- volatility / z ---
    vol_n = min(cfg.vol_lookback_hours, i)
    vol_slice = rets[i - vol_n + 1 : i + 1] if vol_n >= 2 else rets[1:]
    bar_vol = _stdev(vol_slice)
    outgoing_z = abs(outgoing_ret) / bar_vol if bar_vol > 0 else 0.0
    roll_edge_z = abs(known_delta) / bar_vol if bar_vol > 0 else 0.0

    # --- attention: percentrank of |window return| over lookback ---
    att_n = min(cfg.attention_lookback_hours, i - roll)
    abs_windows: list[float] = []
    if att_n >= 50:
        for j in range(i - att_n, i + 1):
            if j - roll < 0:
                continue
            wr = abs(_safe_ret(closes[j], closes[j - roll]))
            abs_windows.append(wr)
    attention = (
        _percentrank(abs_windows, abs(current_wr)) if abs_windows else 50.0
    )

    # --- RVOL (current bar vs SMA) ---
    rv_n = min(cfg.rvol_lookback_hours, i + 1)
    sma_v = sum(vols[i - rv_n + 1 : i + 1]) / max(1, rv_n)
    rvol = vols[i] / sma_v if sma_v > 0 else 0.0

    # --- trend ---
    th = min(cfg.trend_hours, i)
    recent_trend = _safe_ret(closes[i], closes[i - th]) if th >= 1 else 0.0

    # --- classic raw setups ---
    raw_long = is_largest_red and known_delta > 0
    raw_short = is_largest_green and known_delta < 0
    if not cfg.require_window_extreme:
        # path-only mode: side from known delta still
        raw_long = known_delta > 0
        raw_short = known_delta < 0

    # --- filters (Pine) ---
    shock_ok = (
        abs(outgoing_ret) * 100.0 >= cfg.min_shock_pct
        and outgoing_z >= cfg.min_shock_z
    )
    roll_ok = (
        abs(known_delta) * 100.0 >= cfg.min_roll_pct
        and roll_edge_z >= cfg.min_edge_z
    )
    attention_ok = (not cfg.use_attention) or (attention >= cfg.min_attention_rank)
    volume_ok = (not cfg.use_rvol) or (rvol >= cfg.min_rvol)

    long_trend_ok = (not cfg.use_trend_veto) or (
        recent_trend * 100.0 >= -cfg.counter_trend_cap_pct
    )
    short_trend_ok = (not cfg.use_trend_veto) or (
        recent_trend * 100.0 <= cfg.counter_trend_cap_pct
    )

    long_zx = current_wr < 0 and flat_next >= 0
    short_zx = current_wr > 0 and flat_next <= 0
    long_cross_ok = (not cfg.require_zero_cross) or long_zx
    short_cross_ok = (not cfg.require_zero_cross) or short_zx

    filt_long = (
        raw_long
        and shock_ok
        and roll_ok
        and attention_ok
        and volume_ok
        and long_trend_ok
        and long_cross_ok
    )
    filt_short = (
        raw_short
        and shock_ok
        and roll_ok
        and attention_ok
        and volume_ok
        and short_trend_ok
        and short_cross_ok
    )

    strength = pine_strength(outgoing_z, roll_edge_z, attention)

    # filter fail reasons (for tags)
    fail_tags: list[str] = []
    if (raw_long or raw_short) and not (filt_long or filt_short):
        if not shock_ok:
            fail_tags.append("fail-shock")
        if not roll_ok:
            fail_tags.append("fail-edge")
        if not attention_ok:
            fail_tags.append("fail-attention")
        if not volume_ok:
            fail_tags.append("fail-rvol")
        if raw_long and not long_trend_ok:
            fail_tags.append("fail-trend")
        if raw_short and not short_trend_ok:
            fail_tags.append("fail-trend")
        if raw_long and not long_cross_ok:
            fail_tags.append("fail-zerocross")
        if raw_short and not short_cross_ok:
            fail_tags.append("fail-zerocross")

    # outgoing candle meta
    out_idx = i - (roll - 1)
    out_c = candles[out_idx]
    # roll candle open-to-close % for display (may differ slightly from close-close ret)
    roll_move_pct = _safe_pct(out_c.close, out_c.open)
    roll_vol = out_c.quote_volume
    roll_ot = datetime.fromtimestamp(
        out_c.open_time / 1000, tz=timezone.utc
    ).strftime("%Y-%m-%d %H:%M UTC")

    return {
        "current_wr": current_wr,
        "flat_next": flat_next,
        "known_delta": known_delta,
        "outgoing_ret": outgoing_ret,
        "outgoing_z": outgoing_z,
        "roll_edge_z": roll_edge_z,
        "attention": attention,
        "rvol": rvol,
        "recent_trend": recent_trend,
        "is_largest_green": is_largest_green,
        "is_largest_red": is_largest_red,
        "is_extreme": is_extreme,
        "raw_long": raw_long,
        "raw_short": raw_short,
        "filt_long": filt_long,
        "filt_short": filt_short,
        "strength": strength,
        "fail_tags": fail_tags,
        "roll_move_pct": roll_move_pct,
        "roll_vol": roll_vol,
        "roll_ot": roll_ot,
        "bar_vol": bar_vol,
        "long_zx": long_zx,
        "short_zx": short_zx,
    }


def score_idea(
    symbol: str,
    venue: str,
    candles: list[Candle],
    cfg: AdaptiveConfig | None = None,
) -> Idea | None:
    cfg = cfg or AdaptiveConfig()
    pine = compute_pine_metrics(candles, cfg)
    if pine is None:
        return None

    closes = [c.close for c in candles]
    price = closes[-1]
    path = project_24h_path(
        closes, price, roll_hours=cfg.roll_hours, horizon=cfg.horizon
    )
    if len(path) < 2:
        return None

    cliff_pp, cliff_hour, cliff_abs = cliff_metrics(path)
    next_drift = path[1].step_drift_pp if len(path) > 1 else pine["known_delta"] * 100
    path_end = path[-1].displayed_24h_pct - path[0].displayed_24h_pct
    current_24h = path[0].displayed_24h_pct
    flat_next_pct = pine["flat_next"] * 100.0
    known_pp = pine["known_delta"] * 100.0

    # Side from classic raw first, else from known delta / path
    if pine["filt_long"] or pine["raw_long"]:
        side = "LONG"
    elif pine["filt_short"] or pine["raw_short"]:
        side = "SHORT"
    elif known_pp > 0:
        side = "LONG"
    elif known_pp < 0:
        side = "SHORT"
    else:
        return None

    classic_raw = bool(pine["raw_long"] or pine["raw_short"])
    adaptive_pass = bool(pine["filt_long"] or pine["filt_short"])

    # Mode gating (mirrors Pine dashboard states):
    #   classic  → only adaptive READY (strict tradeable)
    #   adaptive → classic raw + READY (shows FILTERED OUT like the Pine table)
    #   explore  → also path-only mechanical drifts
    if cfg.mode == "classic" and not adaptive_pass:
        return None
    if cfg.mode == "adaptive" and not (adaptive_pass or classic_raw):
        return None
    if cfg.mode == "explore":
        if not adaptive_pass and not classic_raw and cliff_abs < cfg.min_abs_cliff:
            if abs(known_pp) < cfg.min_roll_pct:
                return None

    zero_cross = (side == "LONG" and pine["long_zx"]) or (
        side == "SHORT" and pine["short_zx"]
    )

    if adaptive_pass:
        setup_state = "LONG READY" if side == "LONG" else "SHORT READY"
    elif classic_raw:
        setup_state = "FILTERED OUT"
    elif abs(known_pp) >= cfg.min_roll_pct:
        setup_state = "PATH ONLY"
    else:
        setup_state = "WAIT"

    recent_1h = _safe_pct(closes[-1], closes[-2]) if len(closes) >= 2 else 0.0
    recent_4h = (
        _safe_pct(closes[-1], closes[-5]) if len(closes) >= 5 else recent_1h
    )
    recent_trend_pct = pine["recent_trend"] * 100.0

    mag_s, mag_tags = magnet_attraction(path, side)
    liq_s = liquidity_score(pine["roll_vol"])
    fresh_s, already, fresh_tags = freshness_score(
        side, recent_1h, recent_4h, current_24h
    )

    # clean: classic extreme alignment
    clean_s = 10.0
    clean_tags: list[str] = []
    if pine["is_largest_red"] and side == "LONG":
        clean_s += 16
        clean_tags.append("classic-red-extreme")
    elif pine["is_largest_green"] and side == "SHORT":
        clean_s += 16
        clean_tags.append("classic-green-extreme")
    elif classic_raw:
        clean_s += 8
    else:
        clean_s -= 4
        clean_tags.append("not-window-extreme")

    urgency = 1.0 / (1.0 + 0.45 * cliff_hour)
    cliff_s = _clamp(cliff_abs * 5.0 * urgency + (5.0 if cliff_hour <= 2 else 0), 0, 28)
    path_s = _clamp(abs(path_end) * 1.4, 0, 14)

    strength = pine["strength"]

    # Hybrid score: Pine strength is primary when adaptive; path is bonus
    if adaptive_pass:
        total = (
            0.55 * strength
            + 0.15 * cliff_s
            + 0.10 * path_s
            + 0.08 * mag_s
            + 0.07 * liq_s
            + 0.05 * fresh_s
        )
        # boost true pine passes
        total += 12.0
    elif classic_raw:
        total = (
            0.45 * strength
            + 0.15 * cliff_s
            + 0.10 * path_s
            + 0.10 * liq_s
            + 0.10 * fresh_s
            + 0.10 * clean_s
        )
        total *= 0.75  # filtered out penalty
    else:
        total = (
            0.25 * strength
            + 0.25 * cliff_s
            + 0.20 * path_s
            + 0.15 * liq_s
            + 0.15 * mag_s
        )
        total *= 0.55

    if already:
        total *= 0.70

    proj_at_cliff = next(
        (p.displayed_24h_pct for p in path if p.hours_ahead == cliff_hour),
        path[min(cliff_hour, len(path) - 1)].displayed_24h_pct,
    )

    tags = (
        mag_tags
        + fresh_tags
        + clean_tags
        + list(pine["fail_tags"])
    )
    if adaptive_pass:
        tags.insert(0, "adaptive-pass")
    if classic_raw:
        tags.insert(0, "classic-raw")
    if zero_cross:
        tags.append("zero-cross")
    if cliff_hour <= 2:
        tags.append("imminent-cliff")
    if abs(path_end) >= 5:
        tags.append("multi-hour-grind")
    if pine["attention"] >= 80:
        tags.append("high-attention")
    if pine["rvol"] >= 1.5:
        tags.append("high-rvol")

    # dedupe tags preserving order
    seen: set[str] = set()
    tags = [t for t in tags if not (t in seen or seen.add(t))]  # type: ignore[func-returns-value]

    if side == "LONG":
        reason = (
            f"[{setup_state}] Board +{known_pp:.2f}pp next hour if flat "
            f"({current_24h:+.1f}%→{flat_next_pct:+.1f}%). "
            f"Outgoing {pine['outgoing_ret']*100:+.2f}% ({pine['outgoing_z']:.1f}z) "
            f"edge {pine['roll_edge_z']:.1f}z att {pine['attention']:.0f}p rvol {pine['rvol']:.2f}x."
        )
    else:
        reason = (
            f"[{setup_state}] Board {known_pp:.2f}pp next hour if flat "
            f"({current_24h:+.1f}%→{flat_next_pct:+.1f}%). "
            f"Outgoing {pine['outgoing_ret']*100:+.2f}% ({pine['outgoing_z']:.1f}z) "
            f"edge {pine['roll_edge_z']:.1f}z att {pine['attention']:.0f}p rvol {pine['rvol']:.2f}x."
        )

    return Idea(
        symbol=symbol,
        venue=venue,
        side=side,
        price=price,
        next_drift_pp=round(known_pp, 3),  # pine next-hour known delta
        roll_move_pct=round(pine["roll_move_pct"], 3),
        roll_volume=round(pine["roll_vol"], 0),
        roll_open_time=pine["roll_ot"],
        path=path,
        cliff_pp=round(cliff_pp, 3),
        cliff_hour=cliff_hour,
        path_end_drift_pp=round(path_end, 3),
        current_24h_pct=round(current_24h, 3),
        projected_24h_at_cliff=round(proj_at_cliff, 3),
        flat_next_24h_pct=round(flat_next_pct, 3),
        known_roll_delta_pp=round(known_pp, 3),
        outgoing_return_pct=round(pine["outgoing_ret"] * 100.0, 3),
        outgoing_z=round(pine["outgoing_z"], 3),
        roll_edge_z=round(pine["roll_edge_z"], 3),
        attention_rank=round(pine["attention"], 2),
        rvol=round(pine["rvol"], 3),
        recent_trend_pct=round(recent_trend_pct, 3),
        strength_pine=round(strength, 2),
        is_window_extreme=bool(pine["is_extreme"]),
        classic_raw=classic_raw,
        adaptive_pass=adaptive_pass,
        zero_cross=zero_cross,
        setup_state=setup_state,
        score=round(total, 2),
        liquidity_score=round(liq_s, 2),
        magnet_score=round(mag_s, 2),
        clean_score=round(clean_s, 2),
        freshness_score=round(fresh_s, 2),
        cliff_score=round(cliff_s, 2),
        recent_1h_pct=round(recent_1h, 3),
        recent_4h_pct=round(recent_4h, 3),
        already_moved_with_flow=already,
        reason=reason,
        tags=tags,
    )


def reweight_liquidity(ideas: list[Idea]) -> None:
    if not ideas:
        return
    n = len(ideas)
    vols = sorted((i.roll_volume for i in ideas), reverse=True)
    for idea in ideas:
        rank = sum(1 for v in vols if v > idea.roll_volume)
        pct = rank / max(1, n - 1) if n > 1 else 0.0
        peer = 8.0 * (1.0 - pct)
        idea.liquidity_score = round(_clamp(idea.liquidity_score * 0.7 + peer, 0, 40), 2)
        # light rescore keep pine primary
        if idea.adaptive_pass:
            base = (
                0.55 * idea.strength_pine
                + 0.15 * idea.cliff_score
                + 0.10 * _clamp(abs(idea.path_end_drift_pp) * 1.4, 0, 14)
                + 0.08 * idea.magnet_score
                + 0.12 * idea.liquidity_score
                + 12.0
            )
        elif idea.classic_raw:
            base = (
                0.45 * idea.strength_pine
                + 0.15 * idea.cliff_score
                + 0.20 * idea.liquidity_score
                + 0.20 * idea.freshness_score
            ) * 0.75
        else:
            base = (
                0.25 * idea.strength_pine
                + 0.25 * idea.cliff_score
                + 0.25 * idea.liquidity_score
                + 0.25 * idea.magnet_score
            ) * 0.55
        if idea.already_moved_with_flow:
            base *= 0.70
        idea.score = round(base, 2)


def herd_regime(ideas: list[Idea]) -> dict[str, Any]:
    # Prefer adaptive-pass set for regime; fall back to all
    pool = [i for i in ideas if i.adaptive_pass] or ideas
    if not pool:
        return {
            "bias": "neutral",
            "long_share": 0.5,
            "short_share": 0.5,
            "n": 0,
            "n_adaptive": 0,
            "note": "no ideas",
        }
    longs = sum(1 for i in pool if i.side == "LONG")
    n = len(pool)
    long_share = longs / n
    n_ad = sum(1 for i in ideas if i.adaptive_pass)
    if long_share >= 0.62:
        bias = "broad-long-board"
        note = "Many boards set to look better — idiot bid may lift weak alts broadly."
    elif long_share <= 0.38:
        bias = "broad-short-board"
        note = "Many boards set to look worse — expect retail dump pressure across alts."
    else:
        bias = "mixed"
        note = "Mixed roll-offs — pair-level edges more trustworthy than beta."
    return {
        "bias": bias,
        "long_share": round(long_share, 3),
        "short_share": round(1 - long_share, 3),
        "n": n,
        "n_adaptive": n_ad,
        "note": note,
    }


def potato_portfolio(
    ideas: list[Idea],
    max_positions: int = 5,
    max_per_side: int = 3,
    min_score: float = 40.0,
    min_vol: float = 150_000,
    adaptive_only: bool = True,
) -> list[Idea]:
    ranked = sorted(ideas, key=lambda x: x.score, reverse=True)
    picked: list[Idea] = []
    n_long = n_short = 0

    for idea in ranked:
        if adaptive_only and not idea.adaptive_pass:
            continue
        if idea.score < min_score:
            continue
        if idea.roll_volume < min_vol:
            continue
        if idea.already_moved_with_flow and idea.score < min_score + 12:
            continue
        if idea.side == "LONG" and n_long >= max_per_side:
            continue
        if idea.side == "SHORT" and n_short >= max_per_side:
            continue
        picked.append(idea)
        if idea.side == "LONG":
            n_long += 1
        else:
            n_short += 1
        if len(picked) >= max_positions:
            break

    # Fallback: no READY names — surface best classic-raw FILTERED setups by pine strength
    if not picked and adaptive_only:
        ranked_raw = sorted(
            [i for i in ideas if i.classic_raw],
            key=lambda x: (x.strength_pine, x.score),
            reverse=True,
        )
        for idea in ranked_raw:
            if idea.roll_volume < min_vol * 0.5:
                continue
            if idea.side == "LONG" and n_long >= max_per_side:
                continue
            if idea.side == "SHORT" and n_short >= max_per_side:
                continue
            picked.append(idea)
            if idea.side == "LONG":
                n_long += 1
            else:
                n_short += 1
            if len(picked) >= max_positions:
                break
    return picked


def summarize_scan(ideas: list[Idea], venue: str, elapsed_s: float) -> dict[str, Any]:
    herd = herd_regime(ideas)
    n_ad = sum(1 for i in ideas if i.adaptive_pass)
    n_raw = sum(1 for i in ideas if i.classic_raw)
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "venue": venue,
        "elapsed_s": round(elapsed_s, 2),
        "n_ideas": len(ideas),
        "n_adaptive": n_ad,
        "n_classic_raw": n_raw,
        "herd": herd,
        "top_score": ideas[0].score if ideas else 0,
        "median_score": (
            sorted(i.score for i in ideas)[len(ideas) // 2] if ideas else 0
        ),
    }
