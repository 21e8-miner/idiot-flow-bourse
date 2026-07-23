#!/usr/bin/env python3
"""
RJ Idiot Flow Scanner v3 — Pine adaptive + board-path lab
=========================================================
Inspired by Robot James, "A truly idiotic crypto trade":
  https://robotjames.substack.com/p/a-truly-idiotic-crypto-trade

Ports RJ_24H_Roll_Off_Adaptive_v2.pine-style filters into a cross-sectional
scanner, plus multi-hour board path, potato portfolio, and HTML lab.

Usage:
  python scanner.py --html --open
  python scanner.py --mode adaptive
  python scanner.py --mode explore          # show filtered-out classics too
  python scanner.py --mode classic
  python scanner.py --zero-cross --potato
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

from dashboard import build_dashboard
from engine import (
    AdaptiveConfig,
    Candle,
    Idea,
    herd_regime,
    potato_portfolio,
    reweight_liquidity,
    score_idea,
    summarize_scan,
)

STABLE_BASES = {
    "USDC", "FDUSD", "TUSD", "BUSD", "DAI", "USDP", "USDE", "USD1",
    "BFUSD", "EUR", "AEUR", "EURI", "PAXG", "XAUT",
}
WORKERS = 20
TIMEOUT = 18
# Binance allows up to 1000/1500; need ~720h for attention percentile
KLINE_LIMIT_BINANCE = 1000
KLINE_LIMIT_OKX = 300  # OKX public candles cap
_CTX = ssl.create_default_context()
HERE = Path(__file__).resolve().parent


class C:
    RESET = "\033[0m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    MAGENTA = "\033[95m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"
    ORANGE = "\033[33m"


def color_enabled() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


def paint(s: str, *codes: str) -> str:
    if not color_enabled():
        return s
    return "".join(codes) + s + C.RESET


def get_json(url: str, retries: int = 3) -> Any:
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "rj-idiot-flow/3.0",
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
            if isinstance(e, urllib.error.HTTPError) and e.code in (403, 451):
                break
            time.sleep(0.3 * (attempt + 1))
    raise RuntimeError(f"GET failed: {url} ({last_err})")


def _is_stable(base: str) -> bool:
    b = base.upper()
    if b in STABLE_BASES:
        return True
    return b.startswith("USD") and b not in {"", "USDT"}


def _is_noise_symbol(symbol: str) -> bool:
    s = symbol.upper().replace("-USDT-SWAP", "").replace("USDT", "")
    for suf in ("UP", "DOWN", "BULL", "BEAR", "3L", "3S", "2L", "2S", "4L", "4S", "5L", "5S"):
        if s.endswith(suf) and len(s) > len(suf):
            return True
    if len(s) >= 3 and s.endswith("B"):
        root = s[:-1]
        if root.isalpha() and 2 <= len(root) <= 5:
            return True
    return False


def list_binance_futures() -> list[str]:
    info = get_json("https://fapi.binance.com/fapi/v1/exchangeInfo")
    out = []
    for s in info["symbols"]:
        if s.get("contractType") != "PERPETUAL":
            continue
        if s.get("quoteAsset") != "USDT" or s.get("status") != "TRADING":
            continue
        if _is_stable(s.get("baseAsset", "")):
            continue
        sym = s["symbol"]
        if _is_noise_symbol(sym):
            continue
        out.append(sym)
    return sorted(out)


def klines_binance_futures(symbol: str) -> list[Candle]:
    url = (
        f"https://fapi.binance.com/fapi/v1/klines"
        f"?symbol={symbol}&interval=1h&limit={KLINE_LIMIT_BINANCE}"
    )
    raw = get_json(url)
    return [
        Candle(int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[7]))
        for k in raw
    ]


def list_binance_spot() -> list[str]:
    info = get_json("https://data-api.binance.vision/api/v3/exchangeInfo")
    out = []
    for s in info["symbols"]:
        if s.get("quoteAsset") != "USDT" or s.get("status") != "TRADING":
            continue
        if s.get("isSpotTradingAllowed") is False:
            continue
        if _is_stable(s.get("baseAsset", "")):
            continue
        sym = s["symbol"]
        if _is_noise_symbol(sym):
            continue
        out.append(sym)
    return sorted(out)


def klines_binance_spot(symbol: str) -> list[Candle]:
    url = (
        f"https://data-api.binance.vision/api/v3/klines"
        f"?symbol={symbol}&interval=1h&limit={KLINE_LIMIT_BINANCE}"
    )
    raw = get_json(url)
    return [
        Candle(int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[7]))
        for k in raw
    ]


def list_okx_swaps() -> list[str]:
    info = get_json("https://www.okx.com/api/v5/public/instruments?instType=SWAP")
    if info.get("code") != "0":
        raise RuntimeError(info)
    out = []
    for s in info["data"]:
        if s.get("settleCcy") != "USDT" or s.get("state") != "live":
            continue
        inst = s.get("instId", "")
        if not inst.endswith("-USDT-SWAP"):
            continue
        if _is_stable(inst.split("-")[0]):
            continue
        out.append(inst)
    return sorted(out)


def klines_okx(inst_id: str) -> list[Candle]:
    url = (
        "https://www.okx.com/api/v5/market/candles"
        f"?instId={urllib.parse.quote(inst_id)}&bar=1H&limit={KLINE_LIMIT_OKX}"
    )
    raw = get_json(url)
    if raw.get("code") != "0":
        raise RuntimeError(raw)
    candles = []
    for k in reversed(raw["data"]):
        candles.append(
            Candle(
                int(k[0]),
                float(k[1]),
                float(k[2]),
                float(k[3]),
                float(k[4]),
                float(k[7]) if len(k) > 7 else float(k[6]),
            )
        )
    return candles


def binance_spot_vol_map() -> dict[str, float]:
    try:
        rows = get_json("https://data-api.binance.vision/api/v3/ticker/24hr")
        return {r["symbol"]: float(r.get("quoteVolume", 0)) for r in rows}
    except Exception:
        return {}


def okx_vol_map() -> dict[str, float]:
    try:
        raw = get_json("https://www.okx.com/api/v5/market/tickers?instType=SWAP")
        if raw.get("code") != "0":
            return {}
        return {
            r["instId"]: float(r.get("volCcy24h") or r.get("vol24h") or 0)
            for r in raw["data"]
        }
    except Exception:
        return {}


VENUES: dict[str, tuple[Callable, Callable, str]] = {
    "binance-futures": (list_binance_futures, klines_binance_futures, "Binance USDT-M perps"),
    "binance-spot": (list_binance_spot, klines_binance_spot, "Binance spot USDT"),
    "okx": (list_okx_swaps, klines_okx, "OKX USDT swaps"),
}


def resolve_venue(preferred: str) -> tuple[str, Callable, Callable, str]:
    order = [preferred] + [
        v for v in ("binance-futures", "binance-spot", "okx") if v != preferred
    ]
    errors = []
    for name in order:
        list_fn, kline_fn, label = VENUES[name]
        try:
            if name == "binance-futures":
                get_json("https://fapi.binance.com/fapi/v1/ping", retries=1)
            elif name == "binance-spot":
                get_json("https://data-api.binance.vision/api/v3/ping", retries=1)
            else:
                get_json("https://www.okx.com/api/v5/public/time", retries=1)
            return name, list_fn, kline_fn, label
        except Exception as e:
            errors.append(f"{name}: {e}")
    raise RuntimeError("No venue reachable:\n  " + "\n  ".join(errors))


def normalize_symbol(raw: str, venue: str) -> str:
    s = raw.upper().replace("/", "-").replace("_", "-")
    if venue == "okx":
        if s.endswith("-USDT-SWAP"):
            return s
        if s.endswith("USDT") and "-" not in s:
            return f"{s[:-4]}-USDT-SWAP"
        if s.endswith("-USDT"):
            return f"{s}-SWAP"
        return f"{s}-USDT-SWAP"
    s = s.replace("-", "")
    return s if s.endswith("USDT") else s + "USDT"


def prefilter_symbols(symbols: list[str], venue: str, top_n: int) -> list[str]:
    if top_n <= 0 or top_n >= len(symbols):
        return symbols
    if venue == "binance-spot":
        vol = binance_spot_vol_map()
    elif venue == "okx":
        vol = okx_vol_map()
    elif venue == "binance-futures":
        try:
            rows = get_json("https://fapi.binance.com/fapi/v1/ticker/24hr")
            vol = {r["symbol"]: float(r.get("quoteVolume", 0)) for r in rows}
        except Exception:
            return symbols[:top_n]
    else:
        return symbols[:top_n]

    ranked = sorted(symbols, key=lambda s: vol.get(s, 0.0), reverse=True)
    majors = []
    for m in (
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
        "BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP",
    ):
        if m in ranked and m not in majors:
            majors.append(m)
    head = ranked[:top_n]
    for m in majors:
        if m not in head:
            head.append(m)
    return head


def build_config(args: argparse.Namespace) -> AdaptiveConfig:
    return AdaptiveConfig(
        horizon=args.horizon,
        min_abs_cliff=args.min_cliff,
        mode=args.mode,
        min_shock_pct=args.min_shock_pct,
        min_shock_z=args.min_shock_z,
        min_roll_pct=args.min_roll_pct,
        min_edge_z=args.min_edge_z,
        min_attention_rank=args.min_attention,
        min_rvol=args.min_rvol,
        counter_trend_cap_pct=args.trend_cap,
        use_attention=not args.no_attention,
        use_rvol=not args.no_rvol,
        use_trend_veto=not args.no_trend_veto,
        require_zero_cross=args.zero_cross,
        require_window_extreme=not args.no_extreme,
        attention_lookback_hours=args.attention_lookback,
        vol_lookback_hours=args.vol_lookback,
        trend_hours=args.trend_hours,
    )


def scan_universe(
    symbols: list[str],
    kline_fn: Callable[[str], list[Candle]],
    venue: str,
    workers: int,
    cfg: AdaptiveConfig,
) -> list[Idea]:
    ideas: list[Idea] = []
    done = 0
    total = len(symbols)

    def work(sym: str) -> Idea | None:
        try:
            candles = kline_fn(sym)
        except Exception:
            return None
        return score_idea(sym, venue, candles, cfg)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(work, s): s for s in symbols}
        for fut in as_completed(futs):
            done += 1
            if done % 30 == 0 or done == total:
                print(paint(f"  scored {done}/{total}...", C.DIM), file=sys.stderr)
            idea = fut.result()
            if idea is not None:
                ideas.append(idea)

    reweight_liquidity(ideas)
    ideas.sort(key=lambda x: (x.adaptive_pass, x.score), reverse=True)
    return ideas


def fmt_vol(v: float) -> str:
    if v >= 1e6:
        return f"{v/1e6:.2f}M"
    if v >= 1e3:
        return f"{v/1e3:.1f}k"
    return f"{v:.0f}"


def side_paint(side: str) -> str:
    if side == "LONG":
        return paint(f"{side:5}", C.BOLD, C.GREEN)
    return paint(f"{side:5}", C.BOLD, C.RED)


def state_paint(state: str) -> str:
    if "READY" in state and "LONG" in state:
        return paint(f"{state:13}", C.BOLD, C.GREEN)
    if "READY" in state:
        return paint(f"{state:13}", C.BOLD, C.RED)
    if state == "FILTERED OUT":
        return paint(f"{state:13}", C.ORANGE)
    return paint(f"{state:13}", C.DIM)


def print_report(
    ideas: list[Idea],
    potato: list[Idea],
    meta: dict[str, Any],
    top: int,
    label: str,
    mode: str,
) -> None:
    herd = meta["herd"]
    print()
    print(paint("═" * 108, C.CYAN))
    print(
        paint("  RJ IDIOT FLOW LAB v3", C.BOLD, C.WHITE)
        + paint("  ·  Pine adaptive + board path  ·  ", C.DIM)
        + paint(label, C.CYAN)
        + paint(f"  ·  mode={mode}", C.YELLOW)
    )
    print(paint("═" * 108, C.CYAN))
    print(
        f"  as of {meta['generated_at']}  ·  "
        f"{meta['n_ideas']} ideas  ·  "
        f"{meta.get('n_adaptive', 0)} adaptive-pass  ·  "
        f"{meta.get('n_classic_raw', 0)} classic-raw  ·  "
        f"{meta['elapsed_s']}s  ·  regime "
        + paint(str(herd["bias"]), C.YELLOW, C.BOLD)
    )
    print(paint(f"  {herd['note']}", C.DIM))

    print()
    print(
        paint("  POTATO PORTFOLIO", C.BOLD, C.MAGENTA)
        + paint("  — adaptive-pass, mouse-sized", C.DIM)
    )
    print(paint("  " + "─" * 104, C.GRAY))
    if not potato:
        print(
            paint(
                "  (none passed adaptive filters — try --mode explore or loosen thresholds)",
                C.DIM,
            )
        )
    else:
        for i, idea in enumerate(potato, 1):
            tags = ",".join(idea.tags[:5]) if idea.tags else "—"
            print(
                f"  {paint(str(i)+'.', C.BOLD)} {side_paint(idea.side)} "
                f"{paint(f'{idea.symbol:14}', C.BOLD, C.WHITE)} "
                f"{state_paint(idea.setup_state)} "
                f"str {paint(f'{idea.strength_pine:5.1f}', C.CYAN)} "
                f"score {idea.score:5.1f}  "
                f"Δ {idea.known_roll_delta_pp:+.2f}pp  "
                f"out {idea.outgoing_return_pct:+.2f}% ({idea.outgoing_z:.1f}z)  "
                f"att {idea.attention_rank:.0f}p  rvol {idea.rvol:.2f}x"
            )
            print(paint(f"      {idea.reason}", C.DIM))
            print(paint(f"      tags: {tags}", C.GRAY))

    show = ideas[:top]
    print()
    print(paint(f"  FULL BOARD (top {len(show)})", C.BOLD))
    print(paint("  " + "─" * 104, C.GRAY))
    hdr = (
        f"  {'SCORE':>6} {'STR':>5} {'STATE':13} {'SIDE':5} {'SYMBOL':14} "
        f"{'Δpp':>6} {'OUT%':>7} {'zOut':>5} {'zEdge':>5} {'ATT':>4} {'RVOL':>5} "
        f"{'BOARD':>13} {'VOL':>7}"
    )
    print(paint(hdr, C.DIM))
    for idea in show:
        line = (
            f"  {idea.score:6.1f} {idea.strength_pine:5.1f} {idea.setup_state:13} "
            f"{idea.side:5} {idea.symbol:14} "
            f"{idea.known_roll_delta_pp:+6.2f} "
            f"{idea.outgoing_return_pct:+6.2f}% "
            f"{idea.outgoing_z:5.2f} {idea.roll_edge_z:5.2f} "
            f"{idea.attention_rank:4.0f} {idea.rvol:5.2f} "
            f"{idea.current_24h_pct:+5.1f}→{idea.flat_next_24h_pct:+5.1f} "
            f"{fmt_vol(idea.roll_volume):>7}"
        )
        if idea.adaptive_pass:
            col = C.GREEN if idea.side == "LONG" else C.RED
        elif idea.classic_raw:
            col = C.ORANGE
        else:
            col = C.DIM
        print(paint(line, col))

    print()
    print(paint("  LEGEND", C.BOLD))
    print(
        paint(
            "  READY = classic window-extreme + Pine adaptive filters (tradeable).\n"
            "  FILTERED OUT = classic raw but failed shock/edge/attention/rvol/trend.\n"
            "  STR = Pine strength (0.4·outZ + 0.4·edgeZ + 0.2·attention).\n"
            "  Δpp = known next-hour change in displayed 24h % if price flat.\n"
            "  Prefer potato. Hold the hold period — don't fee-bleed. Not advice.",
            C.DIM,
        )
    )
    print()


def run_once(args: argparse.Namespace) -> int:
    cfg = build_config(args)
    preferred = "binance-futures" if args.venue == "auto" else args.venue
    print(paint("Resolving venue...", C.DIM), file=sys.stderr)
    venue, list_fn, kline_fn, label = resolve_venue(preferred)
    if args.venue == "auto" and venue != "binance-futures":
        print(
            paint(f"  futures blocked — using {venue} ({label})", C.YELLOW),
            file=sys.stderr,
        )
    else:
        print(paint(f"  {venue} · {label}", C.DIM), file=sys.stderr)

    # OKX has shorter history — shrink attention lookback automatically
    if venue == "okx" and cfg.attention_lookback_hours > 250:
        cfg.attention_lookback_hours = 250
        print(paint("  OKX: attention lookback capped at 250h", C.DIM), file=sys.stderr)

    if args.symbol:
        symbols = [normalize_symbol(s, venue) for s in args.symbol]
    else:
        print(paint("Loading universe + liquidity prefilter...", C.DIM), file=sys.stderr)
        symbols = list_fn()
        symbols = prefilter_symbols(symbols, venue, args.universe)

    print(
        paint(
            f"  {len(symbols)} symbols · mode={cfg.mode} · "
            f"shock≥{cfg.min_shock_pct}%/{cfg.min_shock_z}z · "
            f"edge≥{cfg.min_roll_pct}%/{cfg.min_edge_z}z · "
            f"att≥{cfg.min_attention_rank}p",
            C.DIM,
        ),
        file=sys.stderr,
    )

    t0 = time.time()
    ideas = scan_universe(symbols, kline_fn, venue, args.workers, cfg)
    if args.min_vol > 0:
        ideas = [i for i in ideas if i.roll_volume >= args.min_vol]
    if args.min_score > 0:
        ideas = [i for i in ideas if i.score >= args.min_score]
    ideas.sort(key=lambda x: (x.adaptive_pass, x.score), reverse=True)

    elapsed = time.time() - t0
    meta = summarize_scan(ideas, venue, elapsed)
    meta["venue_label"] = label
    meta["horizon"] = args.horizon
    meta["mode"] = cfg.mode

    potato = potato_portfolio(
        ideas,
        max_positions=args.potato_n,
        max_per_side=max(1, args.potato_n // 2 + 1),
        min_score=args.potato_min_score,
        min_vol=max(args.min_vol, args.potato_min_vol),
        adaptive_only=(cfg.mode != "explore"),
    )

    idea_dicts = [i.to_dict() for i in ideas]
    potato_dicts = [i.to_dict() for i in potato]

    if args.json:
        out = {"meta": meta, "potato": potato_dicts, "ideas": idea_dicts}
        path = Path(args.json)
        if str(path) == "-":
            json.dump(out, sys.stdout, indent=2)
            print()
        else:
            path.write_text(json.dumps(out, indent=2), encoding="utf-8")
            print(paint(f"Wrote {path}", C.DIM), file=sys.stderr)

    if args.html or args.open:
        html_path = Path(args.html) if args.html else HERE / "idiot_flow_lab.html"
        build_dashboard(idea_dicts, potato_dicts, meta, html_path)
        print(paint(f"Dashboard → {html_path}", C.CYAN), file=sys.stderr)
        if args.open:
            webbrowser.open(html_path.resolve().as_uri())

    if not args.quiet:
        if args.potato_only:
            print()
            print(
                paint("POTATO PORTFOLIO", C.BOLD, C.MAGENTA),
                f"· {label} · {meta['generated_at']}",
            )
            print(paint(herd_regime(ideas)["note"], C.DIM))
            for i, idea in enumerate(potato, 1):
                print(
                    f"  {i}. {side_paint(idea.side)} {idea.symbol:14} "
                    f"{idea.setup_state:13} str {idea.strength_pine:5.1f} "
                    f"Δ{idea.known_roll_delta_pp:+.2f}pp "
                    f"{idea.outgoing_z:.1f}z att{idea.attention_rank:.0f} "
                    f"rvol{idea.rvol:.2f}"
                )
            print()
        else:
            print_report(ideas, potato, meta, top=args.top, label=label, mode=cfg.mode)

    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="RJ Idiot Flow Lab v3 — Pine adaptive roll-off scanner",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--venue",
        choices=["auto", "binance-futures", "binance-spot", "okx"],
        default="auto",
    )
    p.add_argument(
        "--mode",
        choices=["adaptive", "classic", "explore"],
        default="adaptive",
        help="adaptive=READY+FILTERED OUT (Pine-like); classic=READY only; explore=+path",
    )
    p.add_argument("--top", type=int, default=20)
    p.add_argument("--universe", type=int, default=120)
    p.add_argument("--horizon", type=int, default=12)
    p.add_argument("--min-cliff", type=float, default=0.35)
    p.add_argument("--min-vol", type=float, default=80_000)
    p.add_argument("--min-score", type=float, default=0)
    p.add_argument("--workers", type=int, default=WORKERS)
    p.add_argument("--symbol", action="append", default=None)

    # Pine adaptive thresholds (defaults from the .pine)
    p.add_argument("--min-shock-pct", type=float, default=0.75)
    p.add_argument("--min-shock-z", type=float, default=1.50)
    p.add_argument("--min-roll-pct", type=float, default=0.50)
    p.add_argument("--min-edge-z", type=float, default=0.75)
    p.add_argument("--min-attention", type=float, default=60.0)
    p.add_argument("--min-rvol", type=float, default=0.60)
    p.add_argument("--trend-cap", type=float, default=3.0)
    p.add_argument("--trend-hours", type=int, default=6)
    p.add_argument("--attention-lookback", type=int, default=720)
    p.add_argument("--vol-lookback", type=int, default=168)
    p.add_argument("--no-attention", action="store_true")
    p.add_argument("--no-rvol", action="store_true")
    p.add_argument("--no-trend-veto", action="store_true")
    p.add_argument("--no-extreme", action="store_true", help="Skip largest-in-window gate")
    p.add_argument(
        "--zero-cross",
        action="store_true",
        help="Only predicted displayed-return sign flips",
    )

    p.add_argument("--potato", dest="potato_only", action="store_true")
    p.add_argument("--potato-n", type=int, default=5)
    p.add_argument("--potato-min-score", type=float, default=40.0)
    p.add_argument("--potato-min-vol", type=float, default=150_000)
    p.add_argument(
        "--html",
        nargs="?",
        const=str(HERE / "idiot_flow_lab.html"),
        default=None,
    )
    p.add_argument("--open", action="store_true")
    p.add_argument("--json", nargs="?", const="-", default=None)
    p.add_argument("--quiet", action="store_true")
    p.add_argument("--watch", type=int, default=0)
    args = p.parse_args()

    if args.open and not args.html:
        args.html = str(HERE / "idiot_flow_lab.html")

    if args.watch and args.watch > 0:
        while True:
            try:
                run_once(args)
            except KeyboardInterrupt:
                print("\nstopped", file=sys.stderr)
                return 0
            except Exception as e:
                print(paint(f"scan error: {e}", C.RED), file=sys.stderr)
            print(paint(f"sleeping {args.watch}s …", C.DIM), file=sys.stderr)
            time.sleep(args.watch)
    return run_once(args)


if __name__ == "__main__":
    raise SystemExit(main())
