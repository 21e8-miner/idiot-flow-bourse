#!/usr/bin/env python3
"""
Honest Causal Historical Replay & Filter Ablation Backtester for Idiot Flow Bourse.

Zero pip dependencies (Python 3.10+ stdlib only).

Features:
  - Fetches real historical 1h klines from public exchange REST APIs with
    automatic fallback & pagination:
      binance-spot (data-api.binance.vision) -> okx -> coinbase -> kraken
  - Replays `engine.compute_pine_metrics` causally bar-by-bar using ONLY
    candles[:t+1] (strictly zero lookahead; drops final still-forming bar).
  - Measures forward returns at +1h, +4h, +12h, +24h gross and net of
    configurable round-trip fees + slippage (default: 0, 10, 20 bps).
  - Runs a full filter ablation matrix comparing:
      classic_raw, adaptive_full, drop_shock, drop_edge, drop_attention,
      drop_rvol, drop_trend_veto, with_zero_cross, no_window_extreme
  - Computes split-half (H1 vs H2) stability, t-stat, win rate, realized Sharpe,
    Long/Short decomposition, and generates a self-contained Nocturne Tape HTML
    report (`replay_report.html`).
"""

from __future__ import annotations

import argparse
import json
import math
import ssl
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from engine import AdaptiveConfig, Candle, compute_pine_metrics

HERE = Path(__file__).resolve().parent
TIMEOUT = 18
_CTX = ssl.create_default_context()

DEFAULT_BASES: tuple[str, ...] = (
    "BTC", "ETH", "SOL", "BNB", "XRP",
    "DOGE", "ADA", "AVAX", "LINK", "SUI",
    "LTC", "DOT", "UNI", "AAVE", "NEAR",
    "APT", "ARB", "OP", "ATOM", "FIL",
    "ICP", "TRX", "BCH", "ETC", "XLM",
)

HORIZONS: tuple[int, ...] = (1, 4, 12, 24)
DEFAULT_FEES_BPS: tuple[float, ...] = (0.0, 10.0, 20.0)


# ---------------------------------------------------------------------------
# HTTP & Multi-Venue Historical 1h Kline Fetchers
# ---------------------------------------------------------------------------


def _get_json(url: str, retries: int = 3) -> Any:
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "rj-idiot-flow-replay/1.0",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=_CTX) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
        ) as e:
            last_err = e
            if isinstance(e, urllib.error.HTTPError) and e.code in (400, 403, 404, 451):
                break
            time.sleep(0.25 * (attempt + 1))
    raise RuntimeError(f"GET failed: {url} ({last_err})")


def clean_closed_candles(candles: list[Candle], drop_last: bool = True) -> list[Candle]:
    """Sort ascending by open_time, deduplicate, and optionally drop still-forming bar."""
    by_ts: dict[int, Candle] = {}
    for c in candles:
        if c.close > 0 and c.open > 0:
            by_ts[c.open_time] = c
    ordered = [by_ts[k] for k in sorted(by_ts)]
    if drop_last and len(ordered) > 1:
        return ordered[:-1]
    return ordered


def fetch_binance_spot_1h(base: str, target_bars: int) -> list[Candle]:
    symbol = f"{base}USDT"
    collected: list[Candle] = []
    end_time: int | None = None
    while len(collected) < target_bars + 2:
        need = min(1000, target_bars + 2 - len(collected))
        url = (
            f"https://data-api.binance.vision/api/v3/klines"
            f"?symbol={symbol}&interval=1h&limit={need}"
        )
        if end_time is not None:
            url += f"&endTime={end_time}"
        raw = _get_json(url)
        if not raw:
            break
        batch = [
            Candle(
                open_time=int(k[0]),
                open=float(k[1]),
                high=float(k[2]),
                low=float(k[3]),
                close=float(k[4]),
                quote_volume=float(k[7]),
            )
            for k in raw
        ]
        collected.extend(batch)
        oldest = batch[0].open_time
        if end_time is not None and oldest >= end_time:
            break
        end_time = oldest - 1
        if len(batch) < need:
            break
    return clean_closed_candles(collected, drop_last=True)[-target_bars:]


def fetch_okx_1h(base: str, target_bars: int) -> list[Candle]:
    inst_id = f"{base}-USDT-SWAP"
    collected: list[Candle] = []
    after_ts: int | None = None
    max_pages = max(1, math.ceil((target_bars + 5) / 100) + 1)
    for page in range(max_pages):
        if len(collected) >= target_bars + 2:
            break
        if page == 0:
            url = (
                f"https://www.okx.com/api/v5/market/candles"
                f"?instId={urllib.parse.quote(inst_id)}&bar=1H&limit=100"
            )
        else:
            url = (
                f"https://www.okx.com/api/v5/market/history-candles"
                f"?instId={urllib.parse.quote(inst_id)}&bar=1H&limit=100&after={after_ts}"
            )
        raw = _get_json(url)
        if raw.get("code") != "0" or not raw.get("data"):
            break
        batch = []
        for k in raw["data"]:
            ts = int(k[0])
            vol = float(k[7]) if len(k) > 7 else float(k[6])
            batch.append(Candle(ts, float(k[1]), float(k[2]), float(k[3]), float(k[4]), vol))
        collected.extend(batch)
        oldest = min(c.open_time for c in batch)
        if after_ts is not None and oldest >= after_ts:
            break
        after_ts = oldest
    return clean_closed_candles(collected, drop_last=True)[-target_bars:]


def fetch_coinbase_1h(base: str, target_bars: int) -> list[Candle]:
    product = f"{base}-USD"
    collected: list[Candle] = []
    end_sec = int(time.time())
    step_sec = 300 * 3600  # 300 1h bars per request
    pages = max(1, math.ceil((target_bars + 5) / 300))
    for _ in range(pages):
        start_sec = end_sec - step_sec
        s_iso = datetime.fromtimestamp(start_sec, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        e_iso = datetime.fromtimestamp(end_sec, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        url = (
            f"https://api.exchange.coinbase.com/products/{product}/candles"
            f"?granularity=3600&start={s_iso}&end={e_iso}"
        )
        raw = _get_json(url)
        if not isinstance(raw, list) or not raw:
            break
        # Coinbase format: [time_sec, low, high, open, close, volume_base]
        for k in raw:
            ts_ms = int(k[0]) * 1000
            close_p = float(k[4])
            vol_quote = float(k[5]) * close_p
            collected.append(
                Candle(ts_ms, float(k[3]), float(k[2]), float(k[1]), close_p, vol_quote)
            )
        end_sec = start_sec
        time.sleep(0.12)
    return clean_closed_candles(collected, drop_last=True)[-target_bars:]


def fetch_kraken_1h(base: str, target_bars: int) -> list[Candle]:
    kbase = "XBT" if base == "BTC" else base
    pair = f"{kbase}USD"
    url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval=60"
    raw = _get_json(url)
    if raw.get("error"):
        raise RuntimeError(raw["error"])
    result = raw.get("result", {})
    key = next((k for k in result if k != "last"), None)
    if key is None:
        return []
    # Kraken format: [time_sec, open, high, low, close, vwap, volume_base, count]
    collected = []
    for k in result[key]:
        ts_ms = int(k[0]) * 1000
        close_p = float(k[4])
        vol_quote = float(k[6]) * close_p
        collected.append(
            Candle(ts_ms, float(k[1]), float(k[2]), float(k[3]), close_p, vol_quote)
        )
    return clean_closed_candles(collected, drop_last=True)[-target_bars:]


REPLAY_VENUES: dict[str, tuple[Callable[[str, int], list[Candle]], str, str]] = {
    "binance-spot": (
        fetch_binance_spot_1h,
        "https://data-api.binance.vision/api/v3/ping",
        "Binance Spot USDT (data-api.binance.vision)",
    ),
    "okx": (
        fetch_okx_1h,
        "https://www.okx.com/api/v5/public/time",
        "OKX USDT-SWAP",
    ),
    "coinbase": (
        fetch_coinbase_1h,
        "https://api.exchange.coinbase.com/time",
        "Coinbase Exchange USD",
    ),
    "kraken": (
        fetch_kraken_1h,
        "https://api.kraken.com/0/public/Time",
        "Kraken Spot USD",
    ),
}


def resolve_replay_venue(preferred: str = "auto") -> tuple[str, Callable[[str, int], list[Candle]], str]:
    order = (
        ["binance-spot", "okx", "coinbase", "kraken"]
        if preferred == "auto"
        else [preferred] + [v for v in ("binance-spot", "okx", "coinbase", "kraken") if v != preferred]
    )
    errors: list[str] = []
    for name in order:
        fetch_fn, ping_url, label = REPLAY_VENUES[name]
        try:
            _get_json(ping_url, retries=1)
            return name, fetch_fn, label
        except Exception as e:
            errors.append(f"{name}: {e}")
    raise RuntimeError("No replay venue reachable:\n  " + "\n  ".join(errors))


def fetch_universe_klines(
    bases: list[str],
    fetch_fn: Callable[[str, int], list[Candle]],
    target_bars: int,
    workers: int = 10,
) -> dict[str, list[Candle]]:
    data: dict[str, list[Candle]] = {}

    def work(b: str) -> tuple[str, list[Candle]]:
        try:
            cs = fetch_fn(b, target_bars)
            return b, cs
        except Exception:
            return b, []

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(work, b) for b in bases]
        for fut in as_completed(futs):
            b, cs = fut.result()
            if len(cs) >= 200:
                data[b] = cs

    # Drop stale / delisted pairs whose latest bar lags >48h behind universe median
    if len(data) >= 3:
        med_end = int(statistics.median(cs[-1].open_time for cs in data.values()))
        max_lag_ms = 48 * 3_600_000
        data = {b: cs for b, cs in data.items() if (med_end - cs[-1].open_time) <= max_lag_ms}

    return dict(sorted(data.items()))


# ---------------------------------------------------------------------------
# Strategy Variants & Causal Replay Engine
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VariantSpec:
    key: str
    label: str
    description: str
    cfg: AdaptiveConfig
    use_adaptive_gate: bool = True  # False => classic_raw (no adaptive filters)


def build_ablation_variants(base_cfg: AdaptiveConfig | None = None) -> list[VariantSpec]:
    base = base_cfg or AdaptiveConfig()
    return [
        VariantSpec(
            key="classic_raw",
            label="Classic Raw (Baseline)",
            description="Window-extreme + known roll delta only; no adaptive filters",
            cfg=base,
            use_adaptive_gate=False,
        ),
        VariantSpec(
            key="adaptive_full",
            label="Adaptive Full (Pine v2)",
            description="All Pine v2 filters: shock, edge, attention, RVOL, trend veto",
            cfg=base,
            use_adaptive_gate=True,
        ),
        VariantSpec(
            key="drop_shock",
            label="− Drop Shock Filter",
            description="Adaptive Full without min_shock_pct / min_shock_z",
            cfg=replace(base, min_shock_pct=0.0, min_shock_z=0.0),
            use_adaptive_gate=True,
        ),
        VariantSpec(
            key="drop_edge",
            label="− Drop Edge Filter",
            description="Adaptive Full without min_roll_pct / min_edge_z",
            cfg=replace(base, min_roll_pct=0.0, min_edge_z=0.0),
            use_adaptive_gate=True,
        ),
        VariantSpec(
            key="drop_attention",
            label="− Drop Attention Filter",
            description="Adaptive Full with use_attention=False",
            cfg=replace(base, use_attention=False),
            use_adaptive_gate=True,
        ),
        VariantSpec(
            key="drop_rvol",
            label="− Drop RVOL Filter",
            description="Adaptive Full with use_rvol=False",
            cfg=replace(base, use_rvol=False),
            use_adaptive_gate=True,
        ),
        VariantSpec(
            key="drop_trend_veto",
            label="− Drop Trend Veto",
            description="Adaptive Full with use_trend_veto=False",
            cfg=replace(base, use_trend_veto=False),
            use_adaptive_gate=True,
        ),
        VariantSpec(
            key="with_zero_cross",
            label="+ Require Zero-Cross",
            description="Adaptive Full + predicted 24h displayed return sign flip",
            cfg=replace(base, require_zero_cross=True),
            use_adaptive_gate=True,
        ),
        VariantSpec(
            key="no_window_extreme",
            label="− Drop Window Extreme",
            description="Adaptive Full with require_window_extreme=False",
            cfg=replace(base, require_window_extreme=False),
            use_adaptive_gate=True,
        ),
    ]


@dataclass
class TradeEvent:
    symbol: str
    bar_idx: int
    open_time: int
    timestamp_utc: str
    side: str  # LONG | SHORT
    entry_price: float
    known_delta_pp: float
    outgoing_ret_pct: float
    outgoing_z: float
    roll_edge_z: float
    attention_rank: float
    rvol: float
    recent_trend_pct: float
    strength_pine: float
    gross_rets: dict[int, float]  # horizon -> signed gross return (decimal)


def _metric_passes_variant(m: dict[str, Any], spec: VariantSpec) -> str | None:
    """
    Evaluate a VariantSpec's filter gates directly on `compute_pine_metrics` output.
    Exact logical equivalence to calling `compute_pine_metrics(prefix, spec.cfg)`
    when lookback windows match, giving an ~8x speedup across the ablation matrix.
    """
    cfg = spec.cfg
    known_delta = m["known_delta"]
    if cfg.require_window_extreme:
        raw_long = bool(m["is_largest_red"] and known_delta > 0)
        raw_short = bool(m["is_largest_green"] and known_delta < 0)
    else:
        raw_long = known_delta > 0
        raw_short = known_delta < 0

    if not spec.use_adaptive_gate:
        if raw_long:
            return "LONG"
        if raw_short:
            return "SHORT"
        return None

    if not (raw_long or raw_short):
        return None

    shock_ok = (
        abs(m["outgoing_ret"]) * 100.0 >= cfg.min_shock_pct
        and m["outgoing_z"] >= cfg.min_shock_z
    )
    roll_ok = (
        abs(known_delta) * 100.0 >= cfg.min_roll_pct
        and m["roll_edge_z"] >= cfg.min_edge_z
    )
    attention_ok = (not cfg.use_attention) or (m["attention"] >= cfg.min_attention_rank)
    volume_ok = (not cfg.use_rvol) or (m["rvol"] >= cfg.min_rvol)
    if not (shock_ok and roll_ok and attention_ok and volume_ok):
        return None

    recent_pct = m["recent_trend"] * 100.0
    if raw_long:
        trend_ok = (not cfg.use_trend_veto) or (recent_pct >= -cfg.counter_trend_cap_pct)
        cross_ok = (not cfg.require_zero_cross) or bool(m["long_zx"])
        if trend_ok and cross_ok:
            return "LONG"
    if raw_short:
        trend_ok = (not cfg.use_trend_veto) or (recent_pct <= cfg.counter_trend_cap_pct)
        cross_ok = (not cfg.require_zero_cross) or bool(m["short_zx"])
        if trend_ok and cross_ok:
            return "SHORT"
    return None


def _lookback_key(cfg: AdaptiveConfig) -> tuple[int, int, int, int, int]:
    return (
        cfg.roll_hours,
        cfg.vol_lookback_hours,
        cfg.attention_lookback_hours,
        cfg.trend_hours,
        cfg.rvol_lookback_hours,
    )


def replay_symbol(
    symbol: str,
    candles: list[Candle],
    variants: list[VariantSpec],
    *,
    warmup: int,
    horizons: tuple[int, ...] = HORIZONS,
    cooldown_hours: int = 6,
) -> dict[str, list[TradeEvent]]:
    """
    Strictly causal bar-by-bar replay for one symbol across all variants.

    For every bar t in [warmup, len(candles) - 1 - max_h]:
      - Calls `compute_pine_metrics(candles[:t + 1], cfg)` with NO access to
        candles[t + 1:].
      - Groups variants that share identical lookback windows so
        `compute_pine_metrics` runs ONCE per bar across the entire ablation
        matrix while preserving bit-for-bit parity and strict causality.
      - Enforces per-variant cooldown_hours (matching Pine's cooldownHours).
    """
    max_h = max(horizons)
    n = len(candles)
    out: dict[str, list[TradeEvent]] = {v.key: [] for v in variants}
    if n <= warmup + max_h:
        return out

    last_entry: dict[str, int] = {v.key: -10_000_000 for v in variants}

    # Group variants by identical lookback windows (all 9 ablations share 1 group!)
    lb_groups: dict[tuple[int, int, int, int, int], tuple[AdaptiveConfig, list[VariantSpec]]] = {}
    for spec in variants:
        lk = _lookback_key(spec.cfg)
        if lk not in lb_groups:
            # Ensure attention is computed if ANY variant in this group uses it
            lb_groups[lk] = (replace(spec.cfg, use_attention=True), [spec])
        else:
            lb_groups[lk][1].append(spec)
    cfg_groups = list(lb_groups.values())

    for t in range(warmup, n - max_h):
        # Strictly causal prefix: only bars <= t
        prefix = candles[: t + 1]
        entry_c = candles[t]
        entry_px = entry_c.close
        if entry_px <= 0:
            continue

        ts_utc = datetime.fromtimestamp(
            entry_c.open_time / 1000.0, tz=timezone.utc
        ).strftime("%Y-%m-%d %H:%M")

        for cfg, grp in cfg_groups:
            # Skip calling compute_pine_metrics if every variant in this group is on cooldown
            if all((t - last_entry[v.key]) < cooldown_hours for v in grp):
                continue
            m = compute_pine_metrics(prefix, cfg)
            if m is None:
                continue

            for spec in grp:
                if (t - last_entry[spec.key]) < cooldown_hours:
                    continue
                side = _metric_passes_variant(m, spec)
                if side is None:
                    continue
                direction = 1.0 if side == "LONG" else -1.0
                gross_rets: dict[int, float] = {}
                for h in horizons:
                    exit_px = candles[t + h].close
                    gross_rets[h] = direction * (exit_px / entry_px - 1.0)
                out[spec.key].append(
                    TradeEvent(
                        symbol=symbol,
                        bar_idx=t,
                        open_time=entry_c.open_time,
                        timestamp_utc=ts_utc,
                        side=side,
                        entry_price=entry_px,
                        known_delta_pp=round(m["known_delta"] * 100.0, 4),
                        outgoing_ret_pct=round(m["outgoing_ret"] * 100.0, 4),
                        outgoing_z=round(m["outgoing_z"], 3),
                        roll_edge_z=round(m["roll_edge_z"], 3),
                        attention_rank=round(m["attention"], 2),
                        rvol=round(m["rvol"], 3),
                        recent_trend_pct=round(m["recent_trend"] * 100.0, 3),
                        strength_pine=round(m["strength"], 2),
                        gross_rets=gross_rets,
                    )
                )
                last_entry[spec.key] = t

    return out


# ---------------------------------------------------------------------------
# Statistics & Aggregation
# ---------------------------------------------------------------------------


def net_return(gross_ret: float, round_trip_bps: float) -> float:
    """Net trade return after deducting round-trip fee + slippage (in bps)."""
    return gross_ret - (round_trip_bps / 10_000.0)


def summarize_returns(
    rets: list[float],
    span_days: float,
) -> dict[str, Any]:
    n = len(rets)
    if n == 0:
        return {
            "n": 0,
            "mean_bps": 0.0,
            "median_bps": 0.0,
            "std_bps": 0.0,
            "win_rate_pct": 0.0,
            "t_stat": 0.0,
            "sharpe_realized": 0.0,
            "cum_pct": 0.0,
        }
    mean_r = sum(rets) / n
    med_r = statistics.median(rets)
    std_r = statistics.stdev(rets) if n >= 2 else 0.0
    wins = sum(1 for r in rets if r > 0.0)
    t_stat = (mean_r / (std_r / math.sqrt(n))) if (n >= 2 and std_r > 0.0) else 0.0
    trades_per_year = (n * 365.0 / max(span_days, 1.0)) if span_days > 0 else float(n)
    sharpe = (mean_r / std_r) * math.sqrt(trades_per_year) if (n >= 2 and std_r > 0.0) else 0.0
    return {
        "n": n,
        "mean_bps": round(mean_r * 10_000.0, 2),
        "median_bps": round(med_r * 10_000.0, 2),
        "std_bps": round(std_r * 10_000.0, 2),
        "win_rate_pct": round(100.0 * wins / n, 1),
        "t_stat": round(t_stat, 2),
        "sharpe_realized": round(sharpe, 2),
        "cum_pct": round(sum(rets) * 100.0, 2),
    }


def evaluate_variant(
    spec: VariantSpec,
    trades: list[TradeEvent],
    *,
    horizons: tuple[int, ...] = HORIZONS,
    fees_bps: tuple[float, ...] = DEFAULT_FEES_BPS,
    mid_ts: int,
    span_days: float,
) -> dict[str, Any]:
    ordered = sorted(trades, key=lambda x: (x.open_time, x.symbol))
    n_long = sum(1 for tr in ordered if tr.side == "LONG")
    n_short = sum(1 for tr in ordered if tr.side == "SHORT")

    grid: dict[str, dict[str, Any]] = {}
    for h in horizons:
        h_key = f"{h}h"
        grid[h_key] = {}
        for fee in fees_bps:
            f_key = f"{int(fee)}bps"
            rets = [net_return(tr.gross_rets[h], fee) for tr in ordered]
            h1_rets = [net_return(tr.gross_rets[h], fee) for tr in ordered if tr.open_time < mid_ts]
            h2_rets = [net_return(tr.gross_rets[h], fee) for tr in ordered if tr.open_time >= mid_ts]
            long_rets = [net_return(tr.gross_rets[h], fee) for tr in ordered if tr.side == "LONG"]
            short_rets = [net_return(tr.gross_rets[h], fee) for tr in ordered if tr.side == "SHORT"]

            s_all = summarize_returns(rets, span_days)
            s_h1 = summarize_returns(h1_rets, span_days / 2.0)
            s_h2 = summarize_returns(h2_rets, span_days / 2.0)
            s_long = summarize_returns(long_rets, span_days)
            s_short = summarize_returns(short_rets, span_days)

            if s_h1["n"] < 5 or s_h2["n"] < 5:
                stability = "LOW-N"
            elif s_h1["mean_bps"] > 0 and s_h2["mean_bps"] > 0:
                stability = "POS-STABLE"
            elif s_h1["mean_bps"] < 0 and s_h2["mean_bps"] < 0:
                stability = "NEG-STABLE"
            else:
                stability = "UNSTABLE"

            # Cumulative PnL curve in bps (downsampled to <= 120 points for lightweight HTML)
            cum = 0.0
            curve: list[dict[str, Any]] = []
            step = max(1, len(ordered) // 120)
            for idx, (tr, r) in enumerate(zip(ordered, rets)):
                cum += r * 10_000.0
                if idx % step == 0 or idx == len(ordered) - 1:
                    curve.append({"t": tr.timestamp_utc, "bps": round(cum, 1)})

            grid[h_key][f_key] = {
                "all": s_all,
                "h1": s_h1,
                "h2": s_h2,
                "long": s_long,
                "short": s_short,
                "stability": stability,
                "curve": curve,
            }

    return {
        "key": spec.key,
        "label": spec.label,
        "description": spec.description,
        "n_total": len(ordered),
        "n_long": n_long,
        "n_short": n_short,
        "grid": grid,
    }


def run_replay(
    universe_candles: dict[str, list[Candle]],
    *,
    venue: str,
    venue_label: str,
    base_cfg: AdaptiveConfig | None = None,
    horizons: tuple[int, ...] = HORIZONS,
    fees_bps: tuple[float, ...] = DEFAULT_FEES_BPS,
    cooldown_hours: int = 6,
    warmup: int | None = None,
) -> dict[str, Any]:
    """Run full causal replay & filter ablation across all symbols."""
    cfg = base_cfg or AdaptiveConfig()
    if not universe_candles:
        raise ValueError("No candle series provided to run_replay")

    min_len = min(len(cs) for cs in universe_candles.values())
    max_h = max(horizons)

    # Choose warmup: respect full attention_lookback + roll + 2 if bars allow,
    # otherwise shrink attention_lookback gracefully to fit available history.
    if warmup is None:
        ideal_warmup = max(cfg.attention_lookback_hours + cfg.roll_hours + 2, cfg.vol_lookback_hours + 2)
        if min_len - max_h >= ideal_warmup + 168:
            eff_warmup = ideal_warmup
            eff_cfg = cfg
        else:
            # Leave at least half the history (min 168h) for replay
            eff_warmup = min(min_len - max_h - 168, max(cfg.vol_lookback_hours + cfg.roll_hours + 2, 200))
            eff_warmup = max(cfg.roll_hours + 35, eff_warmup)
            eff_att = max(60, eff_warmup - cfg.roll_hours - 2)
            eff_cfg = replace(cfg, attention_lookback_hours=min(cfg.attention_lookback_hours, eff_att))
    else:
        eff_warmup = warmup
        eff_cfg = cfg

    variants = build_ablation_variants(eff_cfg)
    all_trades: dict[str, list[TradeEvent]] = {v.key: [] for v in variants}

    replay_start_ts: int | None = None
    replay_end_ts: int | None = None

    for sym, cs in universe_candles.items():
        if len(cs) <= eff_warmup + max_h:
            continue
        s_ts = cs[eff_warmup].open_time
        e_ts = cs[len(cs) - 1 - max_h].open_time
        replay_start_ts = s_ts if replay_start_ts is None else min(replay_start_ts, s_ts)
        replay_end_ts = e_ts if replay_end_ts is None else max(replay_end_ts, e_ts)

        sym_res = replay_symbol(
            sym,
            cs,
            variants,
            warmup=eff_warmup,
            horizons=horizons,
            cooldown_hours=cooldown_hours,
        )
        for k, evs in sym_res.items():
            all_trades[k].extend(evs)

    if replay_start_ts is None or replay_end_ts is None:
        raise ValueError("Insufficient history across all symbols for replay")

    mid_ts = (replay_start_ts + replay_end_ts) // 2
    span_days = max(1.0, (replay_end_ts - replay_start_ts) / (1000.0 * 86_400.0))

    variant_reports = [
        evaluate_variant(
            spec,
            all_trades[spec.key],
            horizons=horizons,
            fees_bps=fees_bps,
            mid_ts=mid_ts,
            span_days=span_days,
        )
        for spec in variants
    ]

    # Per-symbol breakdown for adaptive_full and classic_raw at +1h (0 bps and 10 bps)
    per_symbol: list[dict[str, Any]] = []
    ad_by_sym: dict[str, list[TradeEvent]] = {}
    cr_by_sym: dict[str, list[TradeEvent]] = {}
    for tr in all_trades["adaptive_full"]:
        ad_by_sym.setdefault(tr.symbol, []).append(tr)
    for tr in all_trades["classic_raw"]:
        cr_by_sym.setdefault(tr.symbol, []).append(tr)

    for sym in sorted(universe_candles):
        ad_evs = ad_by_sym.get(sym, [])
        cr_evs = cr_by_sym.get(sym, [])
        ad_1h_gross = summarize_returns([e.gross_rets[1] for e in ad_evs], span_days)
        ad_1h_10 = summarize_returns([net_return(e.gross_rets[1], 10.0) for e in ad_evs], span_days)
        cr_1h_gross = summarize_returns([e.gross_rets[1] for e in cr_evs], span_days)
        per_symbol.append(
            {
                "symbol": sym,
                "bars": len(universe_candles[sym]),
                "adaptive_n": ad_1h_gross["n"],
                "adaptive_1h_gross_bps": ad_1h_gross["mean_bps"],
                "adaptive_1h_net10_bps": ad_1h_10["mean_bps"],
                "adaptive_1h_wr": ad_1h_gross["win_rate_pct"],
                "classic_n": cr_1h_gross["n"],
                "classic_1h_gross_bps": cr_1h_gross["mean_bps"],
            }
        )

    # Recent adaptive_full trades tape (last 60 trades)
    ad_sorted = sorted(all_trades["adaptive_full"], key=lambda x: x.open_time, reverse=True)
    recent_trades = [
        {
            "timestamp_utc": tr.timestamp_utc,
            "symbol": tr.symbol,
            "side": tr.side,
            "entry_price": tr.entry_price,
            "known_delta_pp": tr.known_delta_pp,
            "outgoing_ret_pct": tr.outgoing_ret_pct,
            "outgoing_z": tr.outgoing_z,
            "roll_edge_z": tr.roll_edge_z,
            "attention_rank": tr.attention_rank,
            "rvol": tr.rvol,
            "strength_pine": tr.strength_pine,
            "r1h_bps": round(tr.gross_rets[1] * 10_000.0, 1),
            "r4h_bps": round(tr.gross_rets[4] * 10_000.0, 1),
            "r12h_bps": round(tr.gross_rets[12] * 10_000.0, 1),
            "r24h_bps": round(tr.gross_rets[24] * 10_000.0, 1),
        }
        for tr in ad_sorted[:60]
    ]

    meta = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "venue": venue,
        "venue_label": venue_label,
        "n_symbols": len(universe_candles),
        "symbols": sorted(universe_candles.keys()),
        "bars_per_symbol_min": min_len,
        "warmup_bars": eff_warmup,
        "attention_lookback_used": eff_cfg.attention_lookback_hours,
        "cooldown_hours": cooldown_hours,
        "horizons": list(horizons),
        "fees_bps": [int(f) for f in fees_bps],
        "start_utc": datetime.fromtimestamp(replay_start_ts / 1000.0, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M UTC"
        ),
        "end_utc": datetime.fromtimestamp(replay_end_ts / 1000.0, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M UTC"
        ),
        "mid_utc": datetime.fromtimestamp(mid_ts / 1000.0, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M UTC"
        ),
        "span_days": round(span_days, 1),
        "config": asdict(eff_cfg),
    }

    return {
        "meta": meta,
        "variants": variant_reports,
        "per_symbol": per_symbol,
        "recent_trades": recent_trades,
    }


# ---------------------------------------------------------------------------
# HTML Report Generator (Nocturne Tape aesthetic matching dashboard.py)
# ---------------------------------------------------------------------------


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_replay_html(report: dict[str, Any], out_path: Path) -> Path:
    meta = report["meta"]
    payload_json = json.dumps(report, separators=(",", ":"))
    html = HTML_TEMPLATE
    for k, v in {
        "@@PAYLOAD_JSON@@": payload_json,
        "@@VENUE@@": _esc(str(meta["venue_label"])),
        "@@N_SYMS@@": str(meta["n_symbols"]),
        "@@START_UTC@@": _esc(str(meta["start_utc"])),
        "@@END_UTC@@": _esc(str(meta["end_utc"])),
        "@@SPAN_DAYS@@": str(meta["span_days"]),
        "@@WARMUP@@": str(meta["warmup_bars"]),
        "@@COOLDOWN@@": str(meta["cooldown_hours"]),
        "@@GENERATED@@": _esc(str(meta["generated_at"])),
    }.items():
        html = html.replace(k, v)
    out_path = Path(out_path)
    out_path.write_text(html, encoding="utf-8")
    return out_path


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<meta name="theme-color" content="#050608"/>
<title>Idiot Flow · Causal Replay &amp; Filter Ablation</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Azeret+Mono:wght@400;500;600;700&family=Big+Shoulders+Display:wght@700;800;900&family=Instrument+Serif:ital@0;1&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
<style>
:root {
  --bg: #050608;
  --panel: rgba(255,255,255,0.035);
  --panel2: rgba(255,255,255,0.06);
  --stroke: rgba(255,255,255,0.09);
  --stroke2: rgba(255,255,255,0.16);
  --ink: #f4f0e6;
  --ink2: #c8c2b4;
  --muted: #8a8478;
  --lime: #c8f23a;
  --lime-hot: #e8ff6a;
  --lime-dim: rgba(200,242,58,0.14);
  --mag: #ff2d8a;
  --mag-dim: rgba(255,45,138,0.14);
  --gold: #e0b84a;
  --gold-dim: rgba(224,184,74,0.14);
  --cyan: #5ce1e6;
  --display: "Big Shoulders Display", "Arial Narrow", Impact, sans-serif;
  --sans: "Outfit", system-ui, sans-serif;
  --serif: "Instrument Serif", Georgia, serif;
  --mono: "Azeret Mono", ui-monospace, monospace;
}
*, *::before, *::after { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: var(--sans);
  color: var(--ink);
  min-height: 100dvh;
  -webkit-font-smoothing: antialiased;
  background:
    radial-gradient(ellipse 70% 45% at 12% -10%, rgba(200,242,58,0.11), transparent 55%),
    radial-gradient(ellipse 55% 40% at 100% 0%, rgba(255,45,138,0.09), transparent 50%),
    linear-gradient(180deg, #0a0c10 0%, var(--bg) 42%, #040506 100%);
  background-attachment: fixed;
}
.shell { max-width: 1320px; margin: 0 auto; padding: 24px clamp(14px, 2.8vw, 36px) 56px; }
.mast {
  display: grid; grid-template-columns: 1fr auto; gap: 16px 24px; align-items: end;
  padding-bottom: 18px; margin-bottom: 18px; border-bottom: 1px solid var(--stroke);
}
@media (max-width: 820px) { .mast { grid-template-columns: 1fr; } }
.eyebrow {
  font-family: var(--mono); font-size: 0.68rem; letter-spacing: 0.14em;
  text-transform: uppercase; color: var(--muted); margin-bottom: 6px;
}
.mast h1 {
  margin: 0; font-family: var(--display); font-weight: 900;
  font-size: clamp(2.6rem, 6.5vw, 4.6rem); line-height: 0.84;
  letter-spacing: -0.03em; text-transform: uppercase; font-stretch: condensed;
}
.mast h1 em {
  font-style: normal; display: block;
  background: linear-gradient(105deg, var(--ink) 0%, var(--lime-hot) 48%, var(--mag) 100%);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.sub { font-family: var(--serif); font-style: italic; font-size: 1.12rem; color: var(--ink2); margin: 10px 0 0; }
.controls { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; justify-content: flex-end; }
.seg {
  display: inline-flex; background: var(--panel); border: 1px solid var(--stroke2);
  border-radius: 999px; padding: 3px; gap: 2px;
}
.seg button {
  background: transparent; border: 0; color: var(--muted); cursor: pointer;
  font-family: var(--mono); font-size: 0.74rem; font-weight: 600;
  padding: 6px 12px; border-radius: 999px; transition: 0.15s;
}
.seg button.active { background: var(--lime); color: #050608; }
.seg button:hover:not(.active) { color: var(--ink); }

.chips { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }
.chip {
  padding: 9px 13px; border-radius: 12px; background: var(--panel); border: 1px solid var(--stroke);
}
.chip .k { font-family: var(--serif); font-style: italic; font-size: 0.84rem; color: var(--muted); }
.chip .v { font-family: var(--mono); font-size: 0.78rem; font-weight: 600; color: var(--ink); margin-top: 2px; }

.kpis { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 10px; margin-bottom: 20px; }
@media (max-width: 1050px) { .kpis { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 560px) { .kpis { grid-template-columns: repeat(2, 1fr); } }
.kpi {
  padding: 14px 16px; border-radius: 14px; background: var(--panel); border: 1px solid var(--stroke);
}
.kpi .k { font-family: var(--serif); font-style: italic; font-size: 0.9rem; color: var(--muted); }
.kpi .v {
  font-family: var(--display); font-weight: 900; font-size: 2rem; line-height: 1.05;
  letter-spacing: -0.02em; font-stretch: condensed; margin-top: 4px; font-variant-numeric: tabular-nums;
}
.kpi .d { font-family: var(--mono); font-size: 0.7rem; color: var(--muted); margin-top: 4px; }

.pos { color: var(--lime); }
.neg { color: var(--mag); }
.neu { color: var(--gold); }

.panel {
  background: var(--panel); border: 1px solid var(--stroke); border-radius: 16px;
  padding: 18px 20px; margin-bottom: 18px; backdrop-filter: blur(10px);
}
.sec-head { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
.sec-head h2 {
  margin: 0; font-family: var(--display); font-weight: 900; font-size: 1.45rem;
  letter-spacing: 0.02em; text-transform: uppercase; font-stretch: condensed;
}
.sec-head h2 em { font-style: normal; color: var(--lime); }
.sec-head .hint { font-family: var(--serif); font-style: italic; font-size: 0.96rem; color: var(--muted); }

.chart-wrap { width: 100%; height: 240px; }
.chart-wrap svg { width: 100%; height: 100%; display: block; }
.legend { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 10px; font-family: var(--mono); font-size: 0.72rem; color: var(--ink2); }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.legend i { display: inline-block; width: 10px; height: 3px; border-radius: 2px; }

.tbl-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-family: var(--mono); font-size: 0.76rem; font-variant-numeric: tabular-nums; }
th, td { padding: 9px 10px; text-align: right; border-bottom: 1px solid var(--stroke); white-space: nowrap; }
th:first-child, td:first-child { text-align: left; }
th { color: var(--muted); font-weight: 600; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.06em; }
tr.highlight td { background: rgba(200,242,58,0.06); }
tr:hover td { background: rgba(255,255,255,0.03); }
.badge {
  display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 0.66rem; font-weight: 700;
  letter-spacing: 0.04em; border: 1px solid var(--stroke2);
}
.badge.pos-stable { color: var(--lime); background: var(--lime-dim); border-color: rgba(200,242,58,0.4); }
.badge.neg-stable { color: var(--mag); background: var(--mag-dim); border-color: rgba(255,45,138,0.4); }
.badge.unstable { color: var(--gold); background: var(--gold-dim); border-color: rgba(224,184,74,0.4); }
.badge.low-n { color: var(--muted); }
.side-L { color: var(--lime); font-weight: 700; }
.side-S { color: var(--mag); font-weight: 700; }

.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 900px) { .two-col { grid-template-columns: 1fr; } }

.notes { font-size: 0.86rem; color: var(--ink2); line-height: 1.55; }
.notes li { margin-bottom: 6px; }
code { font-family: var(--mono); font-size: 0.82em; color: var(--lime); }
</style>
</head>
<body>
<div class="shell">
  <header class="mast">
    <div>
      <div class="eyebrow">IDIOT FLOW BOURSE · ZERO-LOOKAHEAD EMPIRICAL AUDIT</div>
      <h1>Causal Replay<em>&amp; Filter Ablation</em></h1>
      <p class="sub">Bar-by-bar Pine v2 evaluation on real historical 1h klines — gross vs net of round-trip costs.</p>
    </div>
    <div class="controls">
      <div class="seg" id="h-seg"></div>
      <div class="seg" id="f-seg"></div>
    </div>
  </header>

  <div class="chips">
    <div class="chip"><div class="k">Venue</div><div class="v">@@VENUE@@</div></div>
    <div class="chip"><div class="k">Universe</div><div class="v">@@N_SYMS@@ liquid pairs</div></div>
    <div class="chip"><div class="k">Replay Window</div><div class="v">@@START_UTC@@ → @@END_UTC@@ (@@SPAN_DAYS@@d)</div></div>
    <div class="chip"><div class="k">Warmup / Cooldown</div><div class="v">@@WARMUP@@h / @@COOLDOWN@@h</div></div>
    <div class="chip"><div class="k">Generated</div><div class="v">@@GENERATED@@</div></div>
  </div>

  <div class="kpis" id="kpis"></div>

  <section class="panel">
    <div class="sec-head">
      <h2>Cumulative Trade PnL <em>(Equal-Weight, bps)</em></h2>
      <div class="hint" id="chart-hint"></div>
    </div>
    <div class="chart-wrap" id="pnl-chart"></div>
    <div class="legend" id="pnl-legend"></div>
  </section>

  <section class="panel">
    <div class="sec-head">
      <h2>Filter Ablation <em>Matrix</em></h2>
      <div class="hint">Comparing Classic Raw vs Adaptive Full vs dropping each individual filter</div>
    </div>
    <div class="tbl-wrap">
      <table>
        <thead>
          <tr>
            <th>Variant</th>
            <th>N (L/S)</th>
            <th>Gross bps</th>
            <th>Net bps</th>
            <th>Δ vs Adapt</th>
            <th>Win %</th>
            <th>t-stat</th>
            <th>Sharpe</th>
            <th>H1 bps (n)</th>
            <th>H2 bps (n)</th>
            <th>Stability</th>
          </tr>
        </thead>
        <tbody id="ablation-body"></tbody>
      </table>
    </div>
  </section>

  <div class="two-col">
    <section class="panel">
      <div class="sec-head">
        <h2>Horizon Decay <em>(Adaptive Full)</em></h2>
        <div class="hint">Net mean bps &amp; t-stat across holding periods</div>
      </div>
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr><th>Horizon</th><th>0 bps</th><th>10 bps</th><th>20 bps</th><th>Long bps</th><th>Short bps</th></tr>
          </thead>
          <tbody id="decay-body"></tbody>
        </table>
      </div>
    </section>

    <section class="panel">
      <div class="sec-head">
        <h2>Per-Symbol <em>Breakdown (+1h)</em></h2>
        <div class="hint">Adaptive Full vs Classic Raw by asset</div>
      </div>
      <div class="tbl-wrap" style="max-height: 280px; overflow-y: auto;">
        <table>
          <thead>
            <tr><th>Symbol</th><th>Adapt N</th><th>Adapt Gross</th><th>Adapt Net10</th><th>Win %</th><th>Classic N</th><th>Classic Gross</th></tr>
          </thead>
          <tbody id="sym-body"></tbody>
        </table>
      </div>
    </section>
  </div>

  <section class="panel">
    <div class="sec-head">
      <h2>Recent Adaptive Signals <em>(Audit Tape)</em></h2>
      <div class="hint">Latest 60 causal Adaptive Full trades with realized gross returns (bps)</div>
    </div>
    <div class="tbl-wrap" style="max-height: 360px; overflow-y: auto;">
      <table>
        <thead>
          <tr>
            <th>Entry UTC</th><th>Symbol</th><th>Side</th><th>Δpp</th><th>Out %</th>
            <th>zOut</th><th>zEdge</th><th>Att</th><th>RVOL</th>
            <th>+1h</th><th>+4h</th><th>+12h</th><th>+24h</th>
          </tr>
        </thead>
        <tbody id="tape-body"></tbody>
      </table>
    </div>
  </section>

  <section class="panel">
    <div class="sec-head">
      <h2>Methodology <em>&amp; Caveats</em></h2>
      <div class="hint">Honest accounting of what this replay does and does not capture</div>
    </div>
    <ul class="notes">
      <li><strong>Strict zero-lookahead causality:</strong> At every closed 1h bar <code>t</code>, <code>compute_pine_metrics</code> receives only <code>candles[:t+1]</code>. The final still-forming bar is dropped before replay.</li>
      <li><strong>Execution model:</strong> Close-to-close fills (matching Pine <code>process_orders_on_close = true</code>) with per-symbol <code>cooldown_hours</code> to prevent overlapping correlated bar-after-bar triggers.</li>
      <li><strong>Cost model:</strong> Round-trip fee + slippage (0 / 10 / 20 bps) deducted linearly from each trade's gross return. Funding rates and partial fills are not modeled.</li>
      <li><strong>Universe caveat:</strong> Fixed liquid major universe introduces mild survivorship/selection bias relative to illiquid altcoins where retail 24h-tile chasing may behave differently.</li>
      <li><strong>Pine window-extreme note:</strong> <code>engine.py</code> checks whether the outgoing bar is the largest bar in the <em>current</em> 24h display window <code>[t-23..t]</code>, whereas <code>RJ_24H_Roll_Off_Adaptive_v2.pine</code> shifts <code>ta.highest(barReturn, 24)[23]</code> to <code>[t-46..t-23]</code>.</li>
    </ul>
  </section>
</div>

<script id="replay-payload" type="application/json">@@PAYLOAD_JSON@@</script>
<script>
(function() {
  const DATA = JSON.parse(document.getElementById("replay-payload").textContent);
  const horizons = DATA.meta.horizons.map(h => h + "h");
  const fees = DATA.meta.fees_bps.map(f => f + "bps");
  let curH = horizons[0] || "1h";
  let curF = fees.includes("10bps") ? "10bps" : fees[0];

  const cls = v => v > 0 ? "pos" : (v < 0 ? "neg" : "neu");
  const fmt = (v, d=1) => (v > 0 ? "+" : "") + Number(v).toFixed(d);

  function renderButtons() {
    const hs = document.getElementById("h-seg");
    hs.innerHTML = horizons.map(h =>
      `<button class="${h===curH?'active':''}" data-h="${h}">+${h}</button>`
    ).join("");
    hs.querySelectorAll("button").forEach(b => b.onclick = () => { curH = b.dataset.h; renderAll(); });

    const fs = document.getElementById("f-seg");
    fs.innerHTML = fees.map(f =>
      `<button class="${f===curF?'active':''}" data-f="${f}">${f}</button>`
    ).join("");
    fs.querySelectorAll("button").forEach(b => b.onclick = () => { curF = b.dataset.f; renderAll(); });
  }

  function renderKPIs() {
    const ad = DATA.variants.find(v => v.key === "adaptive_full");
    const cr = DATA.variants.find(v => v.key === "classic_raw");
    const a = ad.grid[curH][curF];
    const c = cr.grid[curH][curF];
    const aGross = ad.grid[curH]["0bps"].all;

    const cards = [
      { k: "Adaptive Net Mean", v: `${fmt(a.all.mean_bps)} bps`, d: `Gross ${fmt(aGross.mean_bps)} bps · Med ${fmt(a.all.median_bps)}`, c: cls(a.all.mean_bps) },
      { k: "Adaptive t-stat", v: fmt(a.all.t_stat, 2), d: `N=${a.all.n} (${ad.n_long}L / ${ad.n_short}S)`, c: cls(a.all.t_stat) },
      { k: "Adaptive Win Rate", v: `${a.all.win_rate_pct.toFixed(1)}%`, d: `Realized Sharpe ${fmt(a.all.sharpe_realized, 2)}`, c: a.all.win_rate_pct >= 50 ? "pos" : "neg" },
      { k: "Classic Raw Net", v: `${fmt(c.all.mean_bps)} bps`, d: `N=${c.all.n} · t=${fmt(c.all.t_stat, 2)}`, c: cls(c.all.mean_bps) },
      { k: "Filter Lift (Ad − Raw)", v: `${fmt(a.all.mean_bps - c.all.mean_bps)} bps`, d: `Selection ${(100 * a.all.n / Math.max(1, c.all.n)).toFixed(0)}% of raw`, c: cls(a.all.mean_bps - c.all.mean_bps) },
      { k: "Split-Half (H1 / H2)", v: a.stability, d: `H1 ${fmt(a.h1.mean_bps)} · H2 ${fmt(a.h2.mean_bps)} bps`, c: a.stability === "POS-STABLE" ? "pos" : (a.stability === "NEG-STABLE" ? "neg" : "neu") },
    ];
    document.getElementById("kpis").innerHTML = cards.map(x => `
      <div class="kpi">
        <div class="k">${x.k}</div>
        <div class="v ${x.c}">${x.v}</div>
        <div class="d">${x.d}</div>
      </div>
    `).join("");
  }

  function renderChart() {
    const picks = [
      { key: "adaptive_full", color: "#c8f23a", label: "Adaptive Full" },
      { key: "classic_raw", color: "#5ce1e6", label: "Classic Raw" },
      { key: "drop_attention", color: "#e0b84a", label: "− Drop Attention" },
      { key: "drop_trend_veto", color: "#ff2d8a", label: "− Drop Trend Veto" },
    ];
    const series = picks.map(p => {
      const v = DATA.variants.find(x => x.key === p.key);
      return { ...p, pts: (v && v.grid[curH][curF].curve) || [] };
    });
    const allY = [0];
    series.forEach(s => s.pts.forEach(pt => allY.push(pt.bps)));
    const minY = Math.min(...allY, -50);
    const maxY = Math.max(...allY, 50);
    const spanY = Math.max(1, maxY - minY);
    const W = 1000, H = 220, padL = 56, padR = 16, padT = 14, padB = 24;
    const toY = y => padT + (maxY - y) / spanY * (H - padT - padB);
    const zeroY = toY(0);

    let paths = `<line x1="${padL}" y1="${zeroY.toFixed(1)}" x2="${W-padR}" y2="${zeroY.toFixed(1)}" stroke="rgba(255,255,255,0.2)" stroke-dasharray="4 4"/>`;
    [maxY, 0, minY].forEach(yv => {
      const yy = toY(yv);
      paths += `<text x="${padL-8}" y="${(yy+4).toFixed(1)}" fill="#8a8478" font-size="11" font-family="Azeret Mono, monospace" text-anchor="end">${yv.toFixed(0)}</text>`;
    });

    series.forEach(s => {
      if (s.pts.length < 2) return;
      const d = s.pts.map((pt, i) => {
        const x = padL + (i / (s.pts.length - 1)) * (W - padL - padR);
        const y = toY(pt.bps);
        return `${i===0?'M':'L'}${x.toFixed(1)},${y.toFixed(1)}`;
      }).join(" ");
      paths += `<path d="${d}" fill="none" stroke="${s.color}" stroke-width="${s.key==='adaptive_full'?2.6:1.7}" opacity="${s.key==='adaptive_full'?1:0.82}"/>`;
    });

    document.getElementById("chart-hint").textContent = `Horizon +${curH} · Cost ${curF} round-trip`;
    document.getElementById("pnl-chart").innerHTML = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">${paths}</svg>`;
    document.getElementById("pnl-legend").innerHTML = series.map(s => {
      const last = s.pts.length ? s.pts[s.pts.length - 1].bps : 0;
      return `<span><i style="background:${s.color}"></i>${s.label}: <b>${fmt(last, 0)} bps</b></span>`;
    }).join("");
  }

  function renderAblation() {
    const ad = DATA.variants.find(v => v.key === "adaptive_full");
    const adMean = ad.grid[curH][curF].all.mean_bps;
    document.getElementById("ablation-body").innerHTML = DATA.variants.map(v => {
      const g = v.grid[curH]["0bps"].all;
      const cell = v.grid[curH][curF];
      const a = cell.all;
      const delta = a.mean_bps - adMean;
      const stCls = cell.stability.toLowerCase();
      return `
        <tr class="${v.key==='adaptive_full'?'highlight':''}">
          <td><b>${v.label}</b></td>
          <td>${a.n} <span style="color:var(--muted)">(${v.n_long}/${v.n_short})</span></td>
          <td class="${cls(g.mean_bps)}">${fmt(g.mean_bps)}</td>
          <td class="${cls(a.mean_bps)}"><b>${fmt(a.mean_bps)}</b></td>
          <td class="${v.key==='adaptive_full'?'':cls(delta)}">${v.key==='adaptive_full'?'—':fmt(delta)}</td>
          <td>${a.win_rate_pct.toFixed(1)}%</td>
          <td class="${cls(a.t_stat)}">${fmt(a.t_stat, 2)}</td>
          <td>${fmt(a.sharpe_realized, 2)}</td>
          <td class="${cls(cell.h1.mean_bps)}">${fmt(cell.h1.mean_bps)} (${cell.h1.n})</td>
          <td class="${cls(cell.h2.mean_bps)}">${fmt(cell.h2.mean_bps)} (${cell.h2.n})</td>
          <td><span class="badge ${stCls}">${cell.stability}</span></td>
        </tr>`;
    }).join("");
  }

  function renderDecay() {
    const ad = DATA.variants.find(v => v.key === "adaptive_full");
    document.getElementById("decay-body").innerHTML = horizons.map(h => {
      const f0 = ad.grid[h]["0bps"].all;
      const f10 = ad.grid[h]["10bps"].all;
      const f20 = ad.grid[h]["20bps"].all;
      const cur = ad.grid[h][curF];
      return `
        <tr class="${h===curH?'highlight':''}">
          <td><b>+${h}</b></td>
          <td class="${cls(f0.mean_bps)}">${fmt(f0.mean_bps)} (t=${fmt(f0.t_stat,1)})</td>
          <td class="${cls(f10.mean_bps)}">${fmt(f10.mean_bps)} (t=${fmt(f10.t_stat,1)})</td>
          <td class="${cls(f20.mean_bps)}">${fmt(f20.mean_bps)} (t=${fmt(f20.t_stat,1)})</td>
          <td class="${cls(cur.long.mean_bps)}">${fmt(cur.long.mean_bps)} (${cur.long.n})</td>
          <td class="${cls(cur.short.mean_bps)}">${fmt(cur.short.mean_bps)} (${cur.short.n})</td>
        </tr>`;
    }).join("");
  }

  function renderSymbols() {
    document.getElementById("sym-body").innerHTML = DATA.per_symbol.map(s => `
      <tr>
        <td><b>${s.symbol}</b></td>
        <td>${s.adaptive_n}</td>
        <td class="${cls(s.adaptive_1h_gross_bps)}">${fmt(s.adaptive_1h_gross_bps)}</td>
        <td class="${cls(s.adaptive_1h_net10_bps)}">${fmt(s.adaptive_1h_net10_bps)}</td>
        <td>${s.adaptive_1h_wr.toFixed(0)}%</td>
        <td>${s.classic_n}</td>
        <td class="${cls(s.classic_1h_gross_bps)}">${fmt(s.classic_1h_gross_bps)}</td>
      </tr>
    `).join("");
  }

  function renderTape() {
    document.getElementById("tape-body").innerHTML = DATA.recent_trades.map(t => `
      <tr>
        <td>${t.timestamp_utc}</td>
        <td><b>${t.symbol}</b></td>
        <td class="${t.side==='LONG'?'side-L':'side-S'}">${t.side}</td>
        <td>${fmt(t.known_delta_pp, 2)}</td>
        <td>${fmt(t.outgoing_ret_pct, 2)}%</td>
        <td>${t.outgoing_z.toFixed(2)}</td>
        <td>${t.roll_edge_z.toFixed(2)}</td>
        <td>${t.attention_rank.toFixed(0)}p</td>
        <td>${t.rvol.toFixed(2)}x</td>
        <td class="${cls(t.r1h_bps)}">${fmt(t.r1h_bps, 0)}</td>
        <td class="${cls(t.r4h_bps)}">${fmt(t.r4h_bps, 0)}</td>
        <td class="${cls(t.r12h_bps)}">${fmt(t.r12h_bps, 0)}</td>
        <td class="${cls(t.r24h_bps)}">${fmt(t.r24h_bps, 0)}</td>
      </tr>
    `).join("");
  }

  function renderAll() {
    renderButtons();
    renderKPIs();
    renderChart();
    renderAblation();
    renderDecay();
  }

  renderSymbols();
  renderTape();
  renderAll();
})();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def print_summary(report: dict[str, Any], primary_h: str = "1h", primary_fee: str = "10bps") -> None:
    meta = report["meta"]
    print()
    print("=" * 104)
    print(f"  IDIOT FLOW CAUSAL REPLAY & FILTER ABLATION  ·  {meta['venue_label']}")
    print("=" * 104)
    print(
        f"  Universe: {meta['n_symbols']} pairs · Window: {meta['start_utc']} -> {meta['end_utc']} "
        f"({meta['span_days']}d)"
    )
    print(
        f"  Warmup: {meta['warmup_bars']}h (att_lb={meta['attention_lookback_used']}h) · "
        f"Cooldown: {meta['cooldown_hours']}h · Primary: +{primary_h} @ {primary_fee}"
    )
    print("-" * 104)
    print(
        f"  {'VARIANT':25s} {'N':>5s} {'GROSS':>8s} {'NET10':>8s} {'NET20':>8s} "
        f"{'WIN%':>6s} {'t(N10)':>7s} {'H1/H2 (N10)':>18s} {'STAB':>10s}"
    )
    print("-" * 104)
    for v in report["variants"]:
        g0 = v["grid"][primary_h]["0bps"]["all"]
        g10 = v["grid"][primary_h][primary_fee]
        g20 = v["grid"][primary_h]["20bps"]["all"]
        h1h2 = f"{g10['h1']['mean_bps']:+.1f}/{g10['h2']['mean_bps']:+.1f}"
        print(
            f"  {v['label']:25s} {g10['all']['n']:5d} "
            f"{g0['mean_bps']:+8.2f} {g10['all']['mean_bps']:+8.2f} {g20['mean_bps']:+8.2f} "
            f"{g10['all']['win_rate_pct']:5.1f}% {g10['all']['t_stat']:+7.2f} "
            f"{h1h2:>18s} {g10['stability']:>10s}"
        )
    print("-" * 104)
    print("  Horizon decay (Adaptive Full, gross / net10 / net20 bps):")
    ad = next(v for v in report["variants"] if v["key"] == "adaptive_full")
    for h in meta["horizons"]:
        hk = f"{h}h"
        a0 = ad["grid"][hk]["0bps"]["all"]
        a10 = ad["grid"][hk]["10bps"]["all"]
        a20 = ad["grid"][hk]["20bps"]["all"]
        print(
            f"    +{h:2d}h : gross {a0['mean_bps']:+6.2f} bps (t={a0['t_stat']:+5.2f}) | "
            f"net10 {a10['mean_bps']:+6.2f} bps (t={a10['t_stat']:+5.2f}) | "
            f"net20 {a20['mean_bps']:+6.2f} bps (t={a20['t_stat']:+5.2f})"
        )
    print("=" * 104)
    print()


def main() -> int:
    p = argparse.ArgumentParser(
        description="Idiot Flow Bourse — Causal Historical Replay & Filter Ablation",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--venue",
        choices=["auto", "binance-spot", "okx", "coinbase", "kraken"],
        default="auto",
    )
    p.add_argument("--bars", type=int, default=1440, help="Total 1h bars to fetch per symbol (~60d)")
    p.add_argument("--cooldown", type=int, default=6, help="Cooldown hours after entry per symbol")
    p.add_argument("--workers", type=int, default=10)
    p.add_argument("--symbols", type=str, default="", help="Comma-separated base symbols (e.g. BTC,ETH,SOL)")
    p.add_argument("--html", type=str, default=str(HERE / "replay_report.html"))
    p.add_argument("--json", type=str, default="")
    args = p.parse_args()

    bases = (
        [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
        if args.symbols
        else list(DEFAULT_BASES)
    )

    print("Resolving replay venue...", file=sys.stderr)
    venue, fetch_fn, label = resolve_replay_venue(args.venue)
    print(f"  Using {venue} ({label})", file=sys.stderr)
    print(f"Fetching {args.bars} 1h bars for {len(bases)} pairs...", file=sys.stderr)

    t0 = time.time()
    universe = fetch_universe_klines(bases, fetch_fn, args.bars, workers=args.workers)
    print(
        f"  Fetched {len(universe)}/{len(bases)} pairs in {time.time() - t0:.1f}s "
        f"(min bars={min(len(v) for v in universe.values()) if universe else 0})",
        file=sys.stderr,
    )
    if not universe:
        print("Error: no klines fetched.", file=sys.stderr)
        return 1

    t1 = time.time()
    report = run_replay(
        universe,
        venue=venue,
        venue_label=label,
        cooldown_hours=args.cooldown,
    )
    print(f"  Causal replay completed in {time.time() - t1:.1f}s", file=sys.stderr)

    print_summary(report)

    if args.html:
        out_html = build_replay_html(report, Path(args.html))
        print(f"HTML report -> {out_html}", file=sys.stderr)
    if args.json:
        out_json = Path(args.json)
        out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"JSON report -> {out_json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
