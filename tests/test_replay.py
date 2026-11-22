#!/usr/bin/env python3
"""
Deterministic offline unit tests for replay.py:
  - Strict zero-lookahead causality verification
  - Round-trip fee & slippage arithmetic
  - Filter ablation monotonicity / consistency
  - Cooldown enforcement
  - Candle hygiene & HTML report generation
"""

from __future__ import annotations

import copy
import json
import math
import random
import re
import tempfile
import unittest
from pathlib import Path

from engine import AdaptiveConfig, Candle, compute_pine_metrics
from replay import (
    _metric_passes_variant,
    build_ablation_variants,
    build_replay_html,
    clean_closed_candles,
    net_return,
    replay_symbol,
    run_replay,
    summarize_returns,
)


def _synth_series(n_bars: int = 360, seed: int = 101) -> list[Candle]:
    rng = random.Random(seed)
    closes = [100.0]
    vols = [1_000_000.0]
    for k in range(1, n_bars):
        # Periodic shocks so classic & adaptive triggers fire deterministically
        if k % 37 == 0:
            r = -0.065
        elif k % 53 == 0:
            r = +0.065
        else:
            r = rng.gauss(0.0, 0.005)
        closes.append(max(1.0, closes[-1] * (1.0 + r)))
        vols.append(max(50_000.0, rng.uniform(0.4, 2.2) * 1_000_000.0))

    start_ms = 1_700_000_000_000
    candles: list[Candle] = []
    for i, (c, v) in enumerate(zip(closes, vols)):
        o = closes[i - 1] if i > 0 else c
        candles.append(
            Candle(
                open_time=start_ms + i * 3_600_000,
                open=o,
                high=max(o, c) * 1.002,
                low=min(o, c) * 0.998,
                close=c,
                quote_volume=v,
            )
        )
    return candles


class TestReplayCausality(unittest.TestCase):
    """Prove mathematically that replay_symbol has zero lookahead."""

    def test_future_mutation_does_not_change_past_signals(self) -> None:
        base_candles = _synth_series(n_bars=360, seed=101)
        mutated = copy.deepcopy(base_candles)
        cutoff = 260
        # Violently mutate everything strictly after `cutoff`
        for k in range(cutoff + 1, len(mutated)):
            mutated[k].close *= 5.0
            mutated[k].open *= 5.0
            mutated[k].high *= 5.0
            mutated[k].low *= 5.0
            mutated[k].quote_volume *= 100.0

        cfg = AdaptiveConfig(attention_lookback_hours=120)
        variants = build_ablation_variants(cfg)

        res_base = replay_symbol(
            "TEST", base_candles, variants, warmup=160, cooldown_hours=6
        )
        res_mut = replay_symbol(
            "TEST", mutated, variants, warmup=160, cooldown_hours=6
        )

        total_checked = 0
        for v in variants:
            before_base = [e for e in res_base[v.key] if e.bar_idx <= cutoff]
            before_mut = [e for e in res_mut[v.key] if e.bar_idx <= cutoff]
            self.assertEqual(len(before_base), len(before_mut), f"Count drift in {v.key}")
            for a, b in zip(before_base, before_mut):
                self.assertEqual(a.bar_idx, b.bar_idx)
                self.assertEqual(a.side, b.side)
                self.assertAlmostEqual(a.entry_price, b.entry_price, places=12)
                self.assertAlmostEqual(a.known_delta_pp, b.known_delta_pp, places=12)
                self.assertAlmostEqual(a.outgoing_z, b.outgoing_z, places=12)
                self.assertAlmostEqual(a.roll_edge_z, b.roll_edge_z, places=12)
                self.assertAlmostEqual(a.attention_rank, b.attention_rank, places=12)
                self.assertAlmostEqual(a.rvol, b.rvol, places=12)
                self.assertAlmostEqual(a.strength_pine, b.strength_pine, places=12)
                total_checked += 1

        self.assertGreater(total_checked, 0, "Synthetic series must trigger at least one signal")


class TestReplayFeeAndAblationConsistency(unittest.TestCase):
    """Fee math, ablation subset monotonicity, cooldown, and HTML rendering."""

    def test_net_return_fee_math(self) -> None:
        self.assertAlmostEqual(net_return(0.0123, 0.0), 0.0123, places=12)
        self.assertAlmostEqual(net_return(0.0123, 10.0), 0.0113, places=12)
        self.assertAlmostEqual(net_return(0.0123, 20.0), 0.0103, places=12)
        self.assertAlmostEqual(net_return(-0.005, 10.0), -0.006, places=12)

    def test_summarize_returns_exact(self) -> None:
        empty = summarize_returns([], span_days=30.0)
        self.assertEqual(empty["n"], 0)
        self.assertEqual(empty["t_stat"], 0.0)

        rets = [0.01, 0.03, 0.02]  # mean=0.02 (200 bps), std=0.01 (100 bps)
        s = summarize_returns(rets, span_days=30.0)
        self.assertEqual(s["n"], 3)
        self.assertAlmostEqual(s["mean_bps"], 200.0, places=2)
        self.assertAlmostEqual(s["median_bps"], 200.0, places=2)
        self.assertAlmostEqual(s["std_bps"], 100.0, places=2)
        self.assertEqual(s["win_rate_pct"], 100.0)
        self.assertAlmostEqual(s["t_stat"], round(0.02 / (0.01 / math.sqrt(3)), 2), places=2)

    def test_ablation_subset_monotonicity_zero_cooldown(self) -> None:
        candles = _synth_series(n_bars=420, seed=202)
        cfg = AdaptiveConfig(attention_lookback_hours=120)
        variants = build_ablation_variants(cfg)
        res = replay_symbol("BTC", candles, variants, warmup=160, cooldown_hours=0)

        ad_bars = {(e.bar_idx, e.side) for e in res["adaptive_full"]}
        cr_bars = {(e.bar_idx, e.side) for e in res["classic_raw"]}
        zx_bars = {(e.bar_idx, e.side) for e in res["with_zero_cross"]}

        self.assertGreater(len(cr_bars), 0)
        # Adaptive Full is a subset of Classic Raw
        self.assertTrue(ad_bars.issubset(cr_bars))
        # Adding zero-cross is a subset of Adaptive Full
        self.assertTrue(zx_bars.issubset(ad_bars))
        # Dropping any single filter must produce a superset of Adaptive Full
        for drop_key in (
            "drop_shock",
            "drop_edge",
            "drop_attention",
            "drop_rvol",
            "drop_trend_veto",
            "no_window_extreme",
        ):
            drop_bars = {(e.bar_idx, e.side) for e in res[drop_key]}
            self.assertTrue(
                ad_bars.issubset(drop_bars),
                f"adaptive_full must be a subset of {drop_key}",
            )

    def test_fast_variant_gate_matches_direct_compute_pine_metrics(self) -> None:
        candles = _synth_series(n_bars=260, seed=404)
        cfg = AdaptiveConfig(attention_lookback_hours=120)
        variants = build_ablation_variants(cfg)
        for t in range(160, 230):
            prefix = candles[: t + 1]
            shared_m = compute_pine_metrics(prefix, cfg)
            assert shared_m is not None
            for spec in variants:
                fast_side = _metric_passes_variant(shared_m, spec)
                direct_m = compute_pine_metrics(prefix, spec.cfg)
                assert direct_m is not None
                if not spec.use_adaptive_gate:
                    direct_side = (
                        "LONG" if direct_m["raw_long"]
                        else ("SHORT" if direct_m["raw_short"] else None)
                    )
                else:
                    direct_side = (
                        "LONG" if direct_m["filt_long"]
                        else ("SHORT" if direct_m["filt_short"] else None)
                    )
                self.assertEqual(
                    fast_side,
                    direct_side,
                    f"Gate mismatch at bar {t} for variant {spec.key}",
                )

    def test_cooldown_enforced(self) -> None:
        candles = _synth_series(n_bars=420, seed=303)
        cfg = AdaptiveConfig(attention_lookback_hours=120)
        variants = build_ablation_variants(cfg)
        res = replay_symbol("ETH", candles, variants, warmup=160, cooldown_hours=12)
        for v in variants:
            bars = [e.bar_idx for e in res[v.key]]
            for a, b in zip(bars, bars[1:]):
                self.assertGreaterEqual(b - a, 12, f"Cooldown violated in {v.key}")

    def test_clean_closed_candles(self) -> None:
        raw = [
            Candle(3000, 10, 11, 9, 10.5, 100),
            Candle(1000, 10, 11, 9, 10.1, 100),
            Candle(2000, 10, 11, 9, 10.2, 100),
            Candle(2000, 10, 11, 9, 10.25, 120),  # duplicate ts
            Candle(4000, 10, 11, 9, 0.0, 100),    # invalid close
        ]
        cleaned = clean_closed_candles(raw, drop_last=True)
        self.assertEqual([c.open_time for c in cleaned], [1000, 2000])
        self.assertEqual(cleaned[1].close, 10.25)

    def test_run_replay_and_html_export(self) -> None:
        universe = {
            "BTC": _synth_series(n_bars=400, seed=11),
            "ETH": _synth_series(n_bars=400, seed=22),
            "SOL": _synth_series(n_bars=400, seed=33),
        }
        report = run_replay(
            universe,
            venue="synthetic",
            venue_label="Synthetic Test",
            base_cfg=AdaptiveConfig(attention_lookback_hours=120),
            warmup=160,
            cooldown_hours=6,
        )
        self.assertEqual(report["meta"]["n_symbols"], 3)
        self.assertEqual(len(report["variants"]), 9)

        # Fee offset check: mean_bps(10bps) == mean_bps(0bps) - 10.0 for non-empty variants
        for v in report["variants"]:
            g0 = v["grid"]["1h"]["0bps"]["all"]
            g10 = v["grid"]["1h"]["10bps"]["all"]
            g20 = v["grid"]["1h"]["20bps"]["all"]
            if g0["n"] > 0:
                self.assertAlmostEqual(g10["mean_bps"], g0["mean_bps"] - 10.0, places=1)
                self.assertAlmostEqual(g20["mean_bps"], g0["mean_bps"] - 20.0, places=1)

        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "replay_report.html"
            build_replay_html(report, out_path)
            html = out_path.read_text(encoding="utf-8")
            self.assertIn("Causal Replay", html)
            m = re.search(
                r'<script id="replay-payload" type="application/json">(.*?)</script>',
                html,
                re.S,
            )
            self.assertIsNotNone(m)
            assert m is not None
            parsed = json.loads(m.group(1))
            self.assertEqual(parsed["meta"]["venue"], "synthetic")


if __name__ == "__main__":
    unittest.main()
