#!/usr/bin/env python3
"""
Deterministic Pine <-> Python parity & engine unit tests for idiot-flow-bourse.

Verifies `engine.py` against `RJ_24H_Roll_Off_Adaptive_v2.pine` using Python
stdlib `unittest` only (zero pip dependencies).
"""

from __future__ import annotations

import math
import random
import statistics
import unittest

from engine import (
    AdaptiveConfig,
    Candle,
    _percentrank,
    _stdev,
    bar_returns,
    cliff_metrics,
    compute_pine_metrics,
    freshness_score,
    herd_regime,
    liquidity_score,
    magnet_attraction,
    pine_strength,
    potato_portfolio,
    project_24h_path,
    reweight_liquidity,
    score_idea,
)


def make_candles(
    closes: list[float],
    volumes: list[float] | None = None,
    start_ms: int = 1_700_000_000_000,
) -> list[Candle]:
    """Build synthetic 1h candles from a list of closes (and optional volumes)."""
    n = len(closes)
    if volumes is None:
        volumes = [1_000_000.0] * n
    out: list[Candle] = []
    for i, (c, v) in enumerate(zip(closes, volumes)):
        o = closes[i - 1] if i > 0 else c
        hi = max(o, c) * 1.002
        lo = min(o, c) * 0.998
        out.append(
            Candle(
                open_time=start_ms + i * 3_600_000,
                open=o,
                high=hi,
                low=lo,
                close=c,
                quote_volume=v,
            )
        )
    return out


def make_rolloff_series(
    *,
    n_bars: int = 260,
    outgoing_ret: float = -0.05,
    roll_hours: int = 24,
    recent_drift_bars: int = 0,
    recent_drift_per_bar: float = 0.0,
    base_noise: float = 0.004,
    vol_current: float = 1_500_000.0,
    vol_base: float = 1_000_000.0,
    seed: int = 42,
) -> list[Candle]:
    """
    Generate a deterministic series where bar `i - (roll_hours - 1)` has an
    exact return `outgoing_ret`, and all other bars have small bounded noise.
    """
    rng = random.Random(seed)
    closes = [100.0]
    i_last = n_bars - 1
    out_idx = i_last - (roll_hours - 1)
    for k in range(1, n_bars):
        if k == out_idx:
            r = outgoing_ret
        elif recent_drift_bars > 0 and k > i_last - recent_drift_bars:
            r = recent_drift_per_bar
        else:
            r = rng.uniform(-base_noise, base_noise)
        closes.append(closes[-1] * (1.0 + r))
    vols = [vol_base] * n_bars
    vols[-1] = vol_current
    return make_candles(closes, vols)


class TestRollOffMathParity(unittest.TestCase):
    """Exact algebraic parity with RJ_24H_Roll_Off_Adaptive_v2.pine."""

    def test_known_roll_delta_exact_formula(self) -> None:
        candles = make_rolloff_series(outgoing_ret=-0.06, n_bars=260, seed=7)
        cfg = AdaptiveConfig(attention_lookback_hours=150)
        m = compute_pine_metrics(candles, cfg)
        self.assertIsNotNone(m)
        assert m is not None

        closes = [c.close for c in candles]
        i = len(closes) - 1
        c_now = closes[i]
        c_24 = closes[i - 24]
        c_23 = closes[i - 23]

        expected_current = c_now / c_24 - 1.0
        expected_flat_next = c_now / c_23 - 1.0
        expected_delta = expected_flat_next - expected_current
        expected_outgoing = c_23 / c_24 - 1.0

        self.assertAlmostEqual(m["current_wr"], expected_current, places=12)
        self.assertAlmostEqual(m["flat_next"], expected_flat_next, places=12)
        self.assertAlmostEqual(m["known_delta"], expected_delta, places=12)
        self.assertAlmostEqual(m["outgoing_ret"], expected_outgoing, places=12)
        self.assertAlmostEqual(m["outgoing_ret"], -0.06, places=12)

        # Algebraic identity: flat_next - current == (c_now / c_23) * (-r_out / (1 + r_out))
        # wait: c_now/c_23 - c_now/c_24 = c_now * (1/c_23 - 1/c_24)
        # = (c_now/c_24) * (c_24/c_23 - 1) = (c_now/c_24) * (-r_out / (1 + r_out))
        identity_delta = (c_now / c_24) * (-expected_outgoing / (1.0 + expected_outgoing))
        self.assertAlmostEqual(m["known_delta"], identity_delta, places=12)
        self.assertGreater(m["known_delta"], 0.0)

    def test_project_24h_path_matches_pine_next_hour(self) -> None:
        candles = make_rolloff_series(outgoing_ret=-0.05, n_bars=120, seed=11)
        closes = [c.close for c in candles]
        path = project_24h_path(closes, closes[-1], roll_hours=24, horizon=12)
        self.assertEqual(len(path), 13)
        self.assertEqual([p.hours_ahead for p in path], list(range(13)))

        m = compute_pine_metrics(candles, AdaptiveConfig(use_attention=False))
        assert m is not None
        self.assertAlmostEqual(path[0].displayed_24h_pct, m["current_wr"] * 100.0, places=4)
        self.assertAlmostEqual(path[1].displayed_24h_pct, m["flat_next"] * 100.0, places=4)
        self.assertAlmostEqual(path[1].step_drift_pp, m["known_delta"] * 100.0, places=3)

    def test_stdev_matches_pine_population_stdev(self) -> None:
        xs = [0.01, -0.02, 0.03, -0.01, 0.005, -0.015]
        # TradingView Pine `ta.stdev(src, len)` uses population stdev (div by N)
        self.assertAlmostEqual(_stdev(xs), statistics.pstdev(xs), places=14)
        self.assertNotAlmostEqual(_stdev(xs), statistics.stdev(xs), places=6)

        candles = make_rolloff_series(outgoing_ret=-0.05, n_bars=260, seed=13)
        cfg = AdaptiveConfig(vol_lookback_hours=168, use_attention=False)
        m = compute_pine_metrics(candles, cfg)
        assert m is not None
        rets = bar_returns([c.close for c in candles])
        i = len(candles) - 1
        expected_vol = statistics.pstdev(rets[i - 168 + 1 : i + 1])
        self.assertAlmostEqual(m["bar_vol"], expected_vol, places=14)
        self.assertAlmostEqual(
            m["outgoing_z"], abs(m["outgoing_ret"]) / expected_vol, places=12
        )
        self.assertAlmostEqual(
            m["roll_edge_z"], abs(m["known_delta"]) / expected_vol, places=12
        )

    def test_percentrank_matches_pine_prior_window(self) -> None:
        # Pine ta.percentrank(src, len) compares src[0] against len strictly prior bars.
        self.assertEqual(_percentrank([1.0, 2.0, 3.0, 4.0], 0.5), 0.0)
        self.assertEqual(_percentrank([1.0, 2.0, 3.0, 4.0], 4.5), 100.0)
        self.assertEqual(_percentrank([1.0, 2.0, 3.0, 4.0], 2.0), 50.0)
        self.assertEqual(_percentrank([], 1.0), 50.0)

        # Construct a series where the current |24h return| is strictly smaller
        # than every prior |24h return| in the attention lookback -> rank must be 0.0
        closes = [100.0]
        # Ramp up strongly so all prior 24h returns are large (~+10%), then land back flat at the end
        for k in range(1, 140):
            closes.append(closes[-1] * 1.005)
        # Set the final bar equal to close[i - 24] so current |24h return| == 0.0
        closes.append(closes[-24])
        candles = make_candles(closes)
        cfg = AdaptiveConfig(attention_lookback_hours=80, use_attention=True)
        m = compute_pine_metrics(candles, cfg)
        assert m is not None
        self.assertAlmostEqual(m["current_wr"], 0.0, places=12)
        self.assertEqual(m["attention"], 0.0)

    def test_pine_strength_formula_and_caps(self) -> None:
        # Exact weights: 0.40 * min(outZ/4, 1) + 0.40 * min(edgeZ/3, 1) + 0.20 * att/100
        self.assertAlmostEqual(pine_strength(2.0, 1.5, 50.0), 50.0, places=10)
        self.assertAlmostEqual(pine_strength(4.0, 3.0, 100.0), 100.0, places=10)
        self.assertAlmostEqual(pine_strength(10.0, 10.0, 100.0), 100.0, places=10)
        self.assertAlmostEqual(pine_strength(-2.0, -1.0, -10.0), 0.0, places=10)


class TestWindowExtremeAndFilters(unittest.TestCase):
    """Verify window-extreme detection and every individual Pine adaptive filter."""

    def test_largest_red_gives_long_ready(self) -> None:
        candles = make_rolloff_series(
            outgoing_ret=-0.06,
            n_bars=260,
            base_noise=0.003,
            vol_current=1_500_000.0,
            vol_base=1_000_000.0,
            seed=21,
        )
        cfg = AdaptiveConfig(attention_lookback_hours=150)
        m = compute_pine_metrics(candles, cfg)
        assert m is not None
        self.assertTrue(m["is_largest_red"])
        self.assertFalse(m["is_largest_green"])
        self.assertTrue(m["raw_long"])
        self.assertFalse(m["raw_short"])
        self.assertTrue(m["filt_long"])
        self.assertFalse(m["filt_short"])
        self.assertEqual(m["fail_tags"], [])

        idea = score_idea("BTCUSDT", "test", candles, cfg)
        assert idea is not None
        self.assertEqual(idea.side, "LONG")
        self.assertEqual(idea.setup_state, "LONG READY")
        self.assertTrue(idea.adaptive_pass)
        self.assertTrue(idea.classic_raw)

    def test_largest_green_gives_short_ready(self) -> None:
        candles = make_rolloff_series(
            outgoing_ret=+0.06,
            n_bars=260,
            base_noise=0.003,
            vol_current=1_500_000.0,
            vol_base=1_000_000.0,
            seed=22,
        )
        cfg = AdaptiveConfig(attention_lookback_hours=150)
        m = compute_pine_metrics(candles, cfg)
        assert m is not None
        self.assertTrue(m["is_largest_green"])
        self.assertFalse(m["is_largest_red"])
        self.assertTrue(m["raw_short"])
        self.assertTrue(m["filt_short"])

        idea = score_idea("ETHUSDT", "test", candles, cfg)
        assert idea is not None
        self.assertEqual(idea.side, "SHORT")
        self.assertEqual(idea.setup_state, "SHORT READY")
        self.assertTrue(idea.adaptive_pass)

    def test_eclipsed_outgoing_bar_not_window_extreme(self) -> None:
        # Outgoing bar is -4%, but a later bar inside the current 24h window is -8%.
        candles = make_rolloff_series(outgoing_ret=-0.04, n_bars=260, base_noise=0.002, seed=23)
        closes = [c.close for c in candles]
        # Inject an -8% shock 5 bars ago and carry forward
        shock_idx = len(closes) - 5
        factor = 0.92 / (closes[shock_idx] / closes[shock_idx - 1])
        for k in range(shock_idx, len(closes)):
            closes[k] *= factor
        candles2 = make_candles(closes, [c.quote_volume for c in candles])

        cfg = AdaptiveConfig(attention_lookback_hours=150, require_window_extreme=True)
        m = compute_pine_metrics(candles2, cfg)
        assert m is not None
        self.assertFalse(m["is_largest_red"])
        self.assertFalse(m["raw_long"])

        # With require_window_extreme=False, raw_long becomes True
        cfg_no_ext = AdaptiveConfig(attention_lookback_hours=150, require_window_extreme=False)
        m2 = compute_pine_metrics(candles2, cfg_no_ext)
        assert m2 is not None
        self.assertTrue(m2["raw_long"])

    def test_rvol_filter_veto(self) -> None:
        candles = make_rolloff_series(
            outgoing_ret=-0.06,
            n_bars=260,
            vol_current=200_000.0,  # RVOL ~ 0.21 < 0.60
            vol_base=1_000_000.0,
            seed=24,
        )
        cfg = AdaptiveConfig(attention_lookback_hours=150, use_rvol=True, min_rvol=0.60)
        m = compute_pine_metrics(candles, cfg)
        assert m is not None
        self.assertTrue(m["raw_long"])
        self.assertFalse(m["filt_long"])
        self.assertIn("fail-rvol", m["fail_tags"])

        # Disabling RVOL restores pass
        cfg_off = AdaptiveConfig(attention_lookback_hours=150, use_rvol=False)
        m_off = compute_pine_metrics(candles, cfg_off)
        assert m_off is not None
        self.assertTrue(m_off["filt_long"])

    def test_trend_veto_blocks_knife_catching(self) -> None:
        # Strong recent dump (-5% over last 6h) should veto a LONG setup
        candles = make_rolloff_series(
            outgoing_ret=-0.06,
            n_bars=260,
            recent_drift_bars=6,
            recent_drift_per_bar=-0.009,  # ~ -5.3% over 6h
            base_noise=0.002,
            seed=25,
        )
        cfg = AdaptiveConfig(
            attention_lookback_hours=150,
            use_trend_veto=True,
            counter_trend_cap_pct=3.0,
        )
        m = compute_pine_metrics(candles, cfg)
        assert m is not None
        self.assertTrue(m["raw_long"])
        self.assertFalse(m["filt_long"])
        self.assertIn("fail-trend", m["fail_tags"])

        # Disabling trend veto allows it
        cfg_off = AdaptiveConfig(attention_lookback_hours=150, use_trend_veto=False)
        m_off = compute_pine_metrics(candles, cfg_off)
        assert m_off is not None
        self.assertTrue(m_off["filt_long"])

    def test_zero_cross_filter(self) -> None:
        # Red outgoing bar (-6%) with tiny noise -> current_wr < 0 and flat_next near 0.
        # Force flat_next > 0 by adding a small +0.5% drift after the outgoing bar.
        candles = make_rolloff_series(
            outgoing_ret=-0.06,
            n_bars=260,
            recent_drift_bars=3,
            recent_drift_per_bar=+0.004,
            base_noise=0.001,
            seed=26,
        )
        cfg = AdaptiveConfig(attention_lookback_hours=150, require_zero_cross=True)
        m = compute_pine_metrics(candles, cfg)
        assert m is not None
        self.assertLess(m["current_wr"], 0.0)
        self.assertGreaterEqual(m["flat_next"], 0.0)
        self.assertTrue(m["long_zx"])
        self.assertTrue(m["filt_long"])

        # Now make flat_next stay negative (-2% drift) -> zero_cross fails
        candles_neg = make_rolloff_series(
            outgoing_ret=-0.06,
            n_bars=260,
            recent_drift_bars=3,
            recent_drift_per_bar=-0.008,
            base_noise=0.001,
            seed=26,
        )
        m_neg = compute_pine_metrics(candles_neg, cfg)
        assert m_neg is not None
        self.assertFalse(m_neg["long_zx"])
        self.assertFalse(m_neg["filt_long"])
        self.assertIn("fail-zerocross", m_neg["fail_tags"])

    def test_mode_gating_classic_adaptive_explore(self) -> None:
        # Create a FILTERED OUT classic-raw setup (fails RVOL)
        candles = make_rolloff_series(
            outgoing_ret=-0.06,
            n_bars=260,
            vol_current=100_000.0,
            vol_base=1_000_000.0,
            seed=30,
        )
        classic_cfg = AdaptiveConfig(mode="classic", attention_lookback_hours=150)
        adaptive_cfg = AdaptiveConfig(mode="adaptive", attention_lookback_hours=150)
        explore_cfg = AdaptiveConfig(mode="explore", attention_lookback_hours=150)

        self.assertIsNone(score_idea("SOLUSDT", "test", candles, classic_cfg))
        ad_idea = score_idea("SOLUSDT", "test", candles, adaptive_cfg)
        self.assertIsNotNone(ad_idea)
        assert ad_idea is not None
        self.assertEqual(ad_idea.setup_state, "FILTERED OUT")
        self.assertFalse(ad_idea.adaptive_pass)
        self.assertTrue(ad_idea.classic_raw)

        ex_idea = score_idea("SOLUSDT", "test", candles, explore_cfg)
        self.assertIsNotNone(ex_idea)


class TestIndependentPineReferenceSweep(unittest.TestCase):
    """
    Compare `compute_pine_metrics` bar-by-bar against a clean, independent
    reference implementation of the Pine formulas across 50 consecutive bars.
    """

    def test_50_bar_parity_sweep(self) -> None:
        rng = random.Random(2026)
        n = 300
        closes = [100.0]
        vols = [1_000_000.0]
        for k in range(1, n):
            shock = rng.choice([0.0] * 18 + [-0.045, 0.045])
            r = rng.gauss(0.0, 0.008) + shock
            closes.append(max(1.0, closes[-1] * (1.0 + r)))
            vols.append(max(10_000.0, rng.uniform(0.3, 2.5) * 1_000_000.0))
        candles = make_candles(closes, vols)
        cfg = AdaptiveConfig(
            roll_hours=24,
            vol_lookback_hours=168,
            attention_lookback_hours=150,
            trend_hours=6,
            rvol_lookback_hours=24,
        )

        # Sweep last 50 bars
        for end in range(250, 301):
            sub = candles[:end]
            m = compute_pine_metrics(sub, cfg)
            assert m is not None
            i = end - 1

            # Independent reference calculation
            c = closes[:end]
            v = vols[:end]
            br = [0.0] + [c[t] / c[t - 1] - 1.0 for t in range(1, end)]
            ref_cur = c[i] / c[i - 24] - 1.0
            ref_next = c[i] / c[i - 23] - 1.0
            ref_delta = ref_next - ref_cur
            ref_out = br[i - 23]
            ref_vol = statistics.pstdev(br[i - 168 + 1 : i + 1])
            ref_out_z = abs(ref_out) / ref_vol
            ref_edge_z = abs(ref_delta) / ref_vol
            ref_prior_att = [abs(c[j] / c[j - 24] - 1.0) for j in range(i - 150, i)]
            ref_att = 100.0 * sum(1 for x in ref_prior_att if x <= abs(ref_cur)) / len(ref_prior_att)
            ref_rvol = v[i] / (sum(v[i - 23 : i + 1]) / 24.0)
            ref_trend = c[i] / c[i - 6] - 1.0
            ref_str = 100.0 * min(
                1.0,
                0.40 * min(ref_out_z / 4.0, 1.0)
                + 0.40 * min(ref_edge_z / 3.0, 1.0)
                + 0.20 * ref_att / 100.0,
            )

            self.assertAlmostEqual(m["current_wr"], ref_cur, places=12)
            self.assertAlmostEqual(m["flat_next"], ref_next, places=12)
            self.assertAlmostEqual(m["known_delta"], ref_delta, places=12)
            self.assertAlmostEqual(m["outgoing_ret"], ref_out, places=12)
            self.assertAlmostEqual(m["bar_vol"], ref_vol, places=12)
            self.assertAlmostEqual(m["outgoing_z"], ref_out_z, places=10)
            self.assertAlmostEqual(m["roll_edge_z"], ref_edge_z, places=10)
            self.assertAlmostEqual(m["attention"], ref_att, places=10)
            self.assertAlmostEqual(m["rvol"], ref_rvol, places=10)
            self.assertAlmostEqual(m["recent_trend"], ref_trend, places=12)
            self.assertAlmostEqual(m["strength"], ref_str, places=10)


class TestPortfolioAndEdgeCases(unittest.TestCase):
    """Edge cases, scoring helpers, herd regime, and potato portfolio."""

    def test_insufficient_history_returns_none(self) -> None:
        candles = make_candles([100.0] * 40)
        self.assertIsNone(compute_pine_metrics(candles, AdaptiveConfig()))

    def test_flat_prices_no_divide_by_zero(self) -> None:
        candles = make_candles([100.0] * 260)
        m = compute_pine_metrics(candles, AdaptiveConfig(attention_lookback_hours=150))
        assert m is not None
        self.assertEqual(m["bar_vol"], 0.0)
        self.assertEqual(m["outgoing_z"], 0.0)
        self.assertFalse(m["raw_long"])
        self.assertFalse(m["raw_short"])
        self.assertIsNone(score_idea("FLATUSDT", "test", candles))

    def test_zero_close_returns_none(self) -> None:
        closes = [100.0] * 260
        closes[-25] = 0.0
        candles = make_candles(closes)
        self.assertIsNone(compute_pine_metrics(candles, AdaptiveConfig()))

    def test_herd_regime_and_potato_portfolio(self) -> None:
        cfg = AdaptiveConfig(attention_lookback_hours=150)
        ideas = []
        for idx, (sym, ret) in enumerate(
            [
                ("BTCUSDT", -0.06),
                ("ETHUSDT", -0.055),
                ("SOLUSDT", -0.05),
                ("XRPUSDT", +0.06),
            ]
        ):
            c = make_rolloff_series(outgoing_ret=ret, n_bars=260, seed=50 + idx)
            idea = score_idea(sym, "test", c, cfg)
            assert idea is not None
            ideas.append(idea)

        reweight_liquidity(ideas)
        regime = herd_regime(ideas)
        self.assertEqual(regime["bias"], "broad-long-board")
        self.assertEqual(regime["n_adaptive"], 4)

        potato = potato_portfolio(ideas, max_positions=3, max_per_side=2, min_vol=100_000)
        self.assertEqual(len(potato), 3)
        self.assertLessEqual(sum(1 for x in potato if x.side == "LONG"), 2)
        self.assertLessEqual(sum(1 for x in potato if x.side == "SHORT"), 2)

    def test_helper_bounds(self) -> None:
        self.assertEqual(liquidity_score(0.0), 0.0)
        self.assertGreater(liquidity_score(1e8), liquidity_score(1e5))
        s, already, tags = freshness_score("LONG", 2.0, 4.0, -5.0)
        self.assertTrue(already)
        self.assertIn("already-bid", tags)
        self.assertGreaterEqual(s, 0.0)
        self.assertLessEqual(s, 35.0)
        self.assertEqual(cliff_metrics([]), (0.0, 0, 0.0))
        self.assertEqual(magnet_attraction([], "LONG"), (0.0, []))


if __name__ == "__main__":
    unittest.main()
