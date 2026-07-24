#!/usr/bin/env python3
"""
Generate Idiot Flow Lab HTML — style matched to rj new style.png
(Acid Bourse · dark glass orbs · lime/magenta liquid UI).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_dashboard(
    ideas: list[dict[str, Any]],
    potato: list[dict[str, Any]],
    meta: dict[str, Any],
    out_path: Path,
) -> Path:
    payload = {"meta": meta, "ideas": ideas, "potato": potato}
    data_json = json.dumps(payload, separators=(",", ":"))

    herd = meta.get("herd", {})
    herd_bias = _esc(str(herd.get("bias", "n/a")).replace("-", " ").upper())
    herd_note = _esc(str(herd.get("note", "")))
    generated = _esc(str(meta.get("generated_at", "")))
    gen_short = generated.replace(" UTC", "").replace("  ", " ")
    venue = _esc(str(meta.get("venue_label") or meta.get("venue", "")))
    mode = _esc(str(meta.get("mode", "adaptive")).title())
    n_ad = meta.get("n_adaptive", herd.get("n_adaptive", 0))
    n_raw = meta.get("n_classic_raw", 0)
    n_ideas = meta.get("n_ideas", len(ideas))
    long_share = float(herd.get("long_share") or 0.5)
    short_share = float(herd.get("short_share") or 0.5)
    dist_pct = int(round(max(long_share, short_share) * 100))
    dist_label = "DISTRIBUTION" if short_share >= long_share else "ACCUMULATION"
    top_score = float(meta.get("top_score") or 0)
    median_score = float(meta.get("median_score") or 0)
    elapsed = meta.get("elapsed_s", "—")
    horizon = meta.get("horizon", 12)

    # Aggregate flow-ish stats from ideas for the right rail
    total_vol = sum(float(i.get("roll_volume") or 0) for i in ideas)
    long_vol = sum(float(i.get("roll_volume") or 0) for i in ideas if i.get("side") == "LONG")
    short_vol = sum(float(i.get("roll_volume") or 0) for i in ideas if i.get("side") == "SHORT")
    zs = [abs(float(i.get("outgoing_z") or 0)) for i in ideas]
    avg_z = sum(zs) / len(zs) if zs else 0.0
    vol_label = "ELEVATED" if avg_z >= 1.5 else ("ACTIVE" if avg_z >= 0.8 else "CALM")
    breadth = int(round(long_share * 100))
    breadth_label = "EXPANDING" if long_share >= 0.55 else ("CONTRACTING" if long_share <= 0.45 else "NEUTRAL")
    alt_idx = int(round(median_score * 2.2)) if median_score else 50
    alt_idx = max(0, min(100, alt_idx))
    alt_label = "BULLISH" if alt_idx >= 60 else ("BEARISH" if alt_idx <= 40 else "NEUTRAL")

    def _fmt_vol(v: float) -> str:
        if v >= 1e9:
            return f"${v/1e9:.2f}B"
        if v >= 1e6:
            return f"${v/1e6:.2f}M"
        if v >= 1e3:
            return f"${v/1e3:.1f}K"
        return f"${v:.0f}"

    total_vol_s = _fmt_vol(total_vol)
    long_vol_s = _fmt_vol(long_vol) if long_vol else "+$0"
    short_vol_s = _fmt_vol(short_vol) if short_vol else "$0"
    # Prefix signs like the mock
    long_vol_s = ("+" if not long_vol_s.startswith("+") and long_vol else "") + long_vol_s if long_vol else "+$0"
    short_vol_s = ("-" if short_vol and not short_vol_s.startswith("-") else "") + short_vol_s if short_vol else "$0"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Idiot Flow · Acid Bourse</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet"/>
<style>
  :root {{
    --bg0: #0a0b0e;
    --bg1: #12141a;
    --bg2: #1a1d26;
    --surface: rgba(255,255,255,0.035);
    --surface2: rgba(255,255,255,0.055);
    --line: rgba(255,255,255,0.08);
    --line2: rgba(255,255,255,0.12);
    --ink: #f2f0ea;
    --ink2: #c8c4ba;
    --muted: #7a7670;
    --muted2: #5a5650;
    --lime: #c8f04a;
    --lime2: #a8d830;
    --lime-glow: rgba(200,240,74,0.35);
    --magenta: #e84a9a;
    --magenta2: #c4367a;
    --magenta-glow: rgba(232,74,154,0.35);
    --gold: #e8c47a;
    --warm: #c4a882;
    --ok: #7dd87a;
    --danger: #e85a5a;
    --sans: "Inter", system-ui, -apple-system, sans-serif;
    --mono: "IBM Plex Mono", ui-monospace, monospace;
    --radius: 16px;
    --radius-sm: 10px;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; }}
  body {{
    font-family: var(--sans);
    color: var(--ink);
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
    background:
      radial-gradient(ellipse 70% 55% at 12% 18%, rgba(180,140,90,0.22) 0%, transparent 55%),
      radial-gradient(ellipse 50% 40% at 78% 22%, rgba(80,40,90,0.18) 0%, transparent 50%),
      radial-gradient(ellipse 60% 50% at 55% 70%, rgba(40,60,40,0.12) 0%, transparent 55%),
      linear-gradient(165deg, #1a1612 0%, #0c0d11 38%, #08090c 100%);
    background-attachment: fixed;
  }}
  a {{ color: var(--lime); text-decoration: none; }}
  a:hover {{ text-decoration: underline; text-underline-offset: 3px; }}

  .app {{
    max-width: 1440px;
    margin: 0 auto;
    padding: 28px 36px 40px;
    position: relative;
  }}

  /* ── top brand row ── */
  .topline {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 8px;
  }}
  .brand {{
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--ink2);
  }}
  .brand-dot {{
    width: 18px; height: 18px;
    border-radius: 50%;
    background: radial-gradient(circle at 35% 30%, #fff 0%, var(--lime) 40%, transparent 70%),
                radial-gradient(circle at 70% 70%, var(--magenta) 0%, transparent 55%);
    box-shadow: 0 0 12px var(--lime-glow);
    opacity: 0.9;
  }}
  .clock {{
    display: flex;
    align-items: center;
    gap: 14px;
    font-family: var(--mono);
    font-size: 0.68rem;
    letter-spacing: 0.12em;
    color: var(--muted);
    text-transform: uppercase;
  }}
  .wave {{
    width: 48px; height: 16px;
    opacity: 0.55;
  }}

  /* ── main stage ── */
  .stage {{
    display: grid;
    grid-template-columns: 200px 1fr 200px;
    gap: 20px;
    min-height: 420px;
    align-items: stretch;
    margin-top: 18px;
  }}
  @media (max-width: 1100px) {{
    .stage {{ grid-template-columns: 1fr; }}
    .rail-left, .rail-right {{ display: contents; }}
    .nav-list {{ display: flex; flex-wrap: wrap; gap: 8px 18px; margin: 12px 0; }}
    .orb-zone {{ order: -1; }}
  }}

  /* left rail */
  .tagline {{
    font-size: 0.62rem;
    font-weight: 500;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--muted);
    line-height: 1.55;
    margin: 0 0 28px;
    max-width: 11rem;
  }}
  .tagline::after {{
    content: "";
    display: block;
    width: 18px;
    height: 1px;
    background: var(--line2);
    margin-top: 16px;
  }}
  .title-stack h1 {{
    margin: 0;
    font-size: clamp(2.4rem, 4.2vw, 3.4rem);
    font-weight: 300;
    letter-spacing: 0.04em;
    line-height: 0.95;
    color: var(--ink);
    text-transform: uppercase;
  }}
  .title-stack h1 b {{
    font-weight: 600;
    display: block;
  }}
  .title-sub {{
    margin: 18px 0 0;
    font-size: 0.62rem;
    font-weight: 500;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--muted);
    line-height: 1.5;
    max-width: 12rem;
  }}
  .title-sub::after {{
    content: "";
    display: block;
    width: 18px;
    height: 1px;
    background: var(--line2);
    margin-top: 16px;
  }}
  .nav-list {{
    list-style: none;
    margin: 36px 0 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }}
  .nav-list a {{
    font-size: 0.68rem;
    font-weight: 500;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--muted);
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 10px;
    transition: color 0.15s;
  }}
  .nav-list a:hover {{ color: var(--ink2); text-decoration: none; }}
  .nav-list a.active {{
    color: var(--lime);
  }}
  .nav-list a.active::before {{
    content: "";
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--lime);
    box-shadow: 0 0 10px var(--lime-glow);
  }}

  /* center orb */
  .orb-zone {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    position: relative;
    padding: 20px 0 40px;
  }}
  .orb {{
    width: min(340px, 72vw);
    height: min(340px, 72vw);
    border-radius: 46% 54% 48% 52% / 52% 46% 54% 48%;
    position: relative;
    display: grid;
    place-items: center;
    background:
      radial-gradient(ellipse 55% 50% at 38% 32%, rgba(255,255,255,0.55) 0%, transparent 45%),
      radial-gradient(ellipse 40% 35% at 68% 28%, rgba(232,74,154,0.45) 0%, transparent 50%),
      radial-gradient(ellipse 50% 45% at 30% 70%, rgba(180,220,60,0.35) 0%, transparent 55%),
      radial-gradient(ellipse 60% 55% at 70% 75%, rgba(100,160,220,0.25) 0%, transparent 50%),
      linear-gradient(145deg, rgba(40,50,55,0.5) 0%, rgba(20,22,28,0.85) 100%);
    box-shadow:
      0 0 0 1px rgba(255,255,255,0.12) inset,
      0 0 40px rgba(200,240,74,0.12),
      0 0 80px rgba(232,74,154,0.1),
      0 40px 80px rgba(0,0,0,0.45),
      0 0 1px rgba(255,255,255,0.3);
    animation: orb-breathe 8s ease-in-out infinite;
    overflow: hidden;
  }}
  .orb::before {{
    content: "";
    position: absolute;
    inset: 8%;
    border-radius: inherit;
    background: radial-gradient(ellipse 70% 60% at 50% 45%, rgba(10,12,16,0.55) 0%, rgba(10,12,16,0.82) 100%);
    box-shadow: 0 0 30px rgba(0,0,0,0.3) inset;
  }}
  .orb::after {{
    content: "";
    position: absolute;
    width: 28%; height: 18%;
    top: 12%; left: 22%;
    border-radius: 50%;
    background: linear-gradient(180deg, rgba(255,255,255,0.55), transparent);
    filter: blur(6px);
    pointer-events: none;
  }}
  @keyframes orb-breathe {{
    0%, 100% {{ border-radius: 46% 54% 48% 52% / 52% 46% 54% 48%; transform: translateY(0); }}
    50% {{ border-radius: 52% 48% 54% 46% / 48% 52% 48% 52%; transform: translateY(-6px); }}
  }}
  .orb-core {{
    position: relative;
    z-index: 2;
    text-align: center;
    padding: 24px;
  }}
  .orb-label {{
    font-size: 0.58rem;
    font-weight: 600;
    letter-spacing: 0.28em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 10px;
  }}
  .orb-sym {{
    font-size: clamp(2rem, 4.5vw, 2.85rem);
    font-weight: 300;
    letter-spacing: 0.12em;
    line-height: 1;
    color: var(--ink);
    margin: 0;
  }}
  .orb-sym small {{
    display: block;
    font-size: 0.42em;
    font-weight: 500;
    letter-spacing: 0.2em;
    color: var(--muted);
    margin-top: 6px;
  }}
  .orb-side {{
    margin: 14px 0 18px;
    font-size: 1.05rem;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
  }}
  .orb-side.LONG {{ color: var(--lime); text-shadow: 0 0 20px var(--lime-glow); }}
  .orb-side.SHORT {{ color: var(--magenta); text-shadow: 0 0 20px var(--magenta-glow); }}
  .orb-side .arrow {{ font-weight: 400; margin-left: 4px; }}
  .orb-score-label {{
    font-size: 0.58rem;
    font-weight: 600;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 4px;
  }}
  .orb-score {{
    font-size: 3.6rem;
    font-weight: 300;
    letter-spacing: -0.02em;
    line-height: 1;
    color: var(--ink);
  }}
  .orb-conv {{
    margin-top: 8px;
    font-size: 0.62rem;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--muted);
  }}
  .orb-conv b {{
    color: var(--lime);
    font-weight: 600;
  }}
  .orb-conv.low b {{ color: var(--gold); }}
  .orb-conv.mid b {{ color: var(--gold); }}
  .orb-ripple {{
    position: absolute;
    bottom: -8px;
    left: 50%;
    transform: translateX(-50%);
    width: 70%;
    height: 40px;
    border-radius: 50%;
    border: 1px solid rgba(255,255,255,0.06);
    box-shadow: 0 0 20px rgba(0,0,0,0.3);
    pointer-events: none;
  }}
  .orb-ripple::before, .orb-ripple::after {{
    content: "";
    position: absolute;
    inset: -10px -8%;
    border-radius: 50%;
    border: 1px solid rgba(255,255,255,0.04);
  }}
  .orb-ripple::after {{ inset: -22px -16%; opacity: 0.6; }}
  .orb-bubble {{
    position: absolute;
    border-radius: 50%;
    background: radial-gradient(circle at 35% 30%, rgba(255,255,255,0.5), rgba(200,240,74,0.2) 50%, transparent);
    box-shadow: 0 0 12px rgba(200,240,74,0.2);
    pointer-events: none;
  }}
  .orb-bubble.b1 {{ width: 18px; height: 18px; right: 8%; bottom: 28%; opacity: 0.7; }}
  .orb-bubble.b2 {{ width: 10px; height: 10px; left: 12%; bottom: 38%; opacity: 0.5; }}

  /* right rail metrics */
  .rail-right {{
    display: flex;
    flex-direction: column;
    gap: 22px;
    justify-content: center;
    text-align: right;
    padding-top: 12px;
  }}
  .stat {{
    display: flex;
    flex-direction: column;
    gap: 3px;
  }}
  .stat .k {{
    font-size: 0.58rem;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--muted);
  }}
  .stat .v {{
    font-size: 1.35rem;
    font-weight: 500;
    letter-spacing: -0.02em;
    font-family: var(--mono);
    color: var(--ink);
  }}
  .stat .v.pos {{ color: var(--lime); }}
  .stat .v.neg {{ color: var(--magenta); }}
  .stat .s {{
    font-size: 0.58rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--lime);
  }}
  .stat .s.dim {{ color: var(--muted); }}
  .stat .s.warn {{ color: var(--gold); }}
  .stat .s.hot {{ color: var(--magenta); }}

  /* ── flow projection ── */
  .projection {{
    margin-top: 8px;
    padding: 8px 0 4px;
  }}
  .proj-head {{
    display: flex;
    align-items: baseline;
    gap: 8px;
    margin-bottom: 8px;
  }}
  .proj-head h2 {{
    margin: 0;
    font-size: 0.62rem;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--muted);
  }}
  .proj-head .hint {{
    font-size: 0.58rem;
    color: var(--muted2);
    letter-spacing: 0.06em;
  }}
  .proj-chart {{
    height: 150px;
    position: relative;
    border-radius: var(--radius-sm);
    background: linear-gradient(180deg, rgba(255,255,255,0.02), transparent);
  }}
  .proj-chart svg {{ width: 100%; height: 100%; display: block; }}
  .proj-foot {{
    display: flex;
    justify-content: space-between;
    margin-top: 6px;
    font-size: 0.58rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--muted2);
  }}
  .proj-foot b {{ color: var(--muted); font-weight: 500; }}

  /* ── the board (orbs) ── */
  .board-sec {{
    margin-top: 36px;
  }}
  .board-head {{
    display: flex;
    align-items: baseline;
    gap: 12px;
    margin-bottom: 18px;
  }}
  .board-head h2 {{
    margin: 0;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--ink2);
  }}
  .board-head span {{
    font-size: 0.58rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--muted);
  }}
  .board-orbs {{
    display: flex;
    flex-wrap: wrap;
    gap: 18px 22px;
    justify-content: flex-start;
    padding: 8px 0 20px;
  }}
  .token-orb {{
    width: 108px;
    cursor: pointer;
    text-align: center;
    transition: transform 0.2s ease;
    position: relative;
  }}
  .token-orb:hover {{ transform: translateY(-4px); }}
  .token-orb.active .orb-ball {{
    box-shadow:
      0 0 0 1px rgba(255,255,255,0.25) inset,
      0 0 28px var(--lime-glow),
      0 16px 32px rgba(0,0,0,0.4);
  }}
  .token-orb.SHORT.active .orb-ball {{
    box-shadow:
      0 0 0 1px rgba(255,255,255,0.25) inset,
      0 0 28px var(--magenta-glow),
      0 16px 32px rgba(0,0,0,0.4);
  }}
  .orb-ball {{
    width: 96px; height: 96px;
    margin: 0 auto 8px;
    border-radius: 50%;
    display: grid;
    place-items: center;
    position: relative;
    background:
      radial-gradient(circle at 32% 28%, rgba(255,255,255,0.55) 0%, transparent 38%),
      radial-gradient(circle at 70% 70%, rgba(0,0,0,0.25) 0%, transparent 50%),
      radial-gradient(circle at 50% 50%, rgba(180,220,60,0.55) 0%, rgba(40,60,20,0.9) 100%);
    box-shadow:
      0 0 0 1px rgba(255,255,255,0.15) inset,
      0 12px 28px rgba(0,0,0,0.35),
      0 0 20px rgba(200,240,74,0.15);
  }}
  .token-orb.SHORT .orb-ball {{
    background:
      radial-gradient(circle at 32% 28%, rgba(255,255,255,0.55) 0%, transparent 38%),
      radial-gradient(circle at 70% 70%, rgba(0,0,0,0.25) 0%, transparent 50%),
      radial-gradient(circle at 50% 50%, rgba(232,74,154,0.55) 0%, rgba(60,20,40,0.9) 100%);
    box-shadow:
      0 0 0 1px rgba(255,255,255,0.15) inset,
      0 12px 28px rgba(0,0,0,0.35),
      0 0 20px rgba(232,74,154,0.2);
  }}
  .orb-ball .idx {{
    position: absolute;
    top: 10px;
    font-size: 0.55rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    color: rgba(255,255,255,0.55);
    font-family: var(--mono);
  }}
  .orb-ball .sym {{
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: #fff;
    text-shadow: 0 1px 4px rgba(0,0,0,0.4);
    margin-top: 6px;
  }}
  .orb-ball .sc {{
    font-size: 1.15rem;
    font-weight: 600;
    color: #fff;
    letter-spacing: -0.02em;
    text-shadow: 0 1px 4px rgba(0,0,0,0.4);
    line-height: 1;
  }}
  .token-orb .vol {{
    font-family: var(--mono);
    font-size: 0.62rem;
    color: var(--lime);
    font-weight: 500;
  }}
  .token-orb.SHORT .vol {{ color: var(--magenta); }}
  .token-orb .reflect {{
    width: 70%;
    height: 10px;
    margin: 6px auto 0;
    border-radius: 50%;
    background: radial-gradient(ellipse, rgba(200,240,74,0.2), transparent 70%);
    filter: blur(2px);
  }}
  .token-orb.SHORT .reflect {{
    background: radial-gradient(ellipse, rgba(232,74,154,0.2), transparent 70%);
  }}

  /* ── teardown + notes ── */
  .lower {{
    display: grid;
    grid-template-columns: 1.1fr 1.1fr 0.9fr;
    gap: 28px;
    margin-top: 28px;
    padding-top: 24px;
    border-top: 1px solid var(--line);
  }}
  @media (max-width: 900px) {{
    .lower {{ grid-template-columns: 1fr; }}
  }}
  .sec-title {{
    margin: 0 0 16px;
    font-size: 0.62rem;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--muted);
  }}
  .teardown-grid {{
    display: grid;
    grid-template-columns: 130px 1fr;
    gap: 16px;
    align-items: center;
  }}
  @media (max-width: 600px) {{
    .teardown-grid {{ grid-template-columns: 1fr; }}
  }}
  .radar-wrap {{
    width: 130px;
    height: 130px;
  }}
  .radar-wrap svg {{ width: 100%; height: 100%; }}
  .td-list {{
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: 0.72rem;
  }}
  .td-list .row {{
    display: flex;
    justify-content: space-between;
    gap: 12px;
    color: var(--muted);
    padding: 2px 0;
  }}
  .td-list .row b {{
    font-weight: 600;
    color: var(--ink2);
    font-family: var(--mono);
    font-size: 0.7rem;
  }}
  .td-list .row b.pos {{ color: var(--lime); }}
  .td-list .row b.neg {{ color: var(--magenta); }}
  .td-list .row b.hi {{ color: var(--lime); }}
  .td-head {{
    display: flex;
    align-items: baseline;
    gap: 10px;
    margin-bottom: 12px;
  }}
  .td-head .sym {{
    font-size: 0.95rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    color: var(--ink);
  }}
  .td-head .side {{
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.14em;
  }}
  .td-head .side.LONG {{ color: var(--lime); }}
  .td-head .side.SHORT {{ color: var(--magenta); }}
  .overall {{
    margin-top: 14px;
    font-size: 0.68rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--muted);
  }}
  .overall b {{ color: var(--lime); }}

  .notes ul {{
    margin: 0;
    padding: 0 0 0 14px;
    color: var(--ink2);
    font-size: 0.78rem;
    line-height: 1.65;
  }}
  .notes li {{ margin-bottom: 4px; }}
  .notes li::marker {{ color: var(--muted2); }}
  .zen {{
    margin-top: 18px;
    height: 100px;
    border-radius: 12px;
    background:
      radial-gradient(ellipse 40% 30% at 62% 48%, rgba(60,70,50,0.5) 0%, transparent 50%),
      radial-gradient(ellipse 80% 60% at 50% 80%, rgba(80,75,65,0.25) 0%, transparent 60%),
      linear-gradient(180deg, rgba(30,32,28,0.4), rgba(20,22,18,0.6));
    border: 1px solid var(--line);
    position: relative;
    overflow: hidden;
  }}
  .zen-stone {{
    position: absolute;
    width: 22px; height: 16px;
    border-radius: 50%;
    background: radial-gradient(circle at 40% 35%, #6a685e, #2a2824);
    box-shadow: 0 2px 6px rgba(0,0,0,0.4);
    left: 58%; top: 42%;
  }}
  .zen-rings {{
    position: absolute;
    left: 50%; top: 48%;
    width: 90px; height: 50px;
    transform: translate(-50%, -50%);
    border-radius: 50%;
    border: 1px solid rgba(255,255,255,0.06);
    box-shadow:
      0 0 0 8px rgba(255,255,255,0.03),
      0 0 0 16px rgba(255,255,255,0.02),
      0 0 0 24px rgba(255,255,255,0.015);
  }}
  .zen-tree {{
    position: absolute;
    right: 14%; top: 18%;
    width: 36px; height: 48px;
    opacity: 0.55;
  }}

  /* ── audit table ── */
  .audit {{
    margin-top: 40px;
  }}
  .table-card {{
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--radius);
    overflow: hidden;
    backdrop-filter: blur(12px);
  }}
  .table-toolbar {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 12px 14px;
    border-bottom: 1px solid var(--line);
    background: var(--surface2);
  }}
  select, input, button {{
    font-family: var(--sans);
    font-size: 0.72rem;
    border: 1px solid var(--line2);
    background: rgba(0,0,0,0.35);
    color: var(--ink);
    border-radius: 8px;
    padding: 7px 10px;
  }}
  select option {{ background: #1a1d26; }}
  button {{
    background: var(--lime);
    color: #0a0b0e;
    border-color: var(--lime);
    font-weight: 700;
    cursor: pointer;
    letter-spacing: 0.04em;
  }}
  button:hover {{ filter: brightness(1.08); }}
  .table-wrap {{ overflow-x: auto; }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.76rem;
  }}
  th {{
    text-align: left;
    padding: 11px 12px;
    font-size: 0.58rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--muted);
    background: rgba(0,0,0,0.2);
    border-bottom: 1px solid var(--line);
    white-space: nowrap;
  }}
  td {{
    padding: 11px 12px;
    border-bottom: 1px solid var(--line);
    color: var(--ink2);
    white-space: nowrap;
    vertical-align: middle;
  }}
  tr:hover td {{ background: rgba(255,255,255,0.03); }}
  td.score {{
    font-weight: 700;
    font-size: 1rem;
    color: var(--lime);
    letter-spacing: -0.03em;
    font-family: var(--mono);
  }}
  td.sym {{ font-weight: 600; color: var(--ink); }}
  .bars {{
    display: inline-flex;
    gap: 2px;
    vertical-align: middle;
  }}
  .bars i {{
    width: 7px; height: 10px;
    border-radius: 1px;
    background: rgba(255,255,255,0.1);
    display: inline-block;
  }}
  .bars i.on {{ background: var(--lime); box-shadow: 0 0 6px var(--lime-glow); }}
  .pos {{ color: var(--lime); font-weight: 600; }}
  .neg {{ color: var(--magenta); font-weight: 600; }}
  .path-cell svg {{ width: 72px; height: 28px; display: block; }}

  .pill {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 0.58rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 3px 8px;
    border-radius: 999px;
    border: 1px solid var(--line2);
    background: rgba(255,255,255,0.04);
    color: var(--muted);
    white-space: nowrap;
  }}
  .pill.short, .pill.SHORT {{
    color: var(--magenta);
    border-color: rgba(232,74,154,0.35);
    background: rgba(232,74,154,0.1);
  }}
  .pill.long, .pill.LONG {{
    color: var(--lime);
    border-color: rgba(200,240,74,0.35);
    background: rgba(200,240,74,0.1);
  }}
  .pill.ready {{
    color: var(--lime);
    border-color: rgba(200,240,74,0.35);
    background: rgba(200,240,74,0.1);
  }}
  .pill.filtered {{
    color: var(--muted);
    border-color: var(--line2);
    background: rgba(255,255,255,0.03);
  }}
  .pill.cleared {{
    color: var(--ok);
    border-color: rgba(125,216,122,0.35);
    background: rgba(125,216,122,0.1);
  }}

  /* footer */
  .foot {{
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    margin-top: 28px;
    padding-top: 18px;
    border-top: 1px solid var(--line);
    font-size: 0.58rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--muted2);
  }}
  .foot .live {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    color: var(--lime);
  }}
  .foot .live::before {{
    content: "";
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--lime);
    box-shadow: 0 0 8px var(--lime-glow);
    animation: pulse 2s ease-in-out infinite;
  }}
  @keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.4; }}
  }}
  .foot .logo {{
    font-weight: 600;
    letter-spacing: 0.16em;
    color: var(--muted);
  }}
  .inspire {{
    margin-top: 8px;
    font-size: 0.62rem;
    letter-spacing: 0.02em;
    text-transform: none;
    color: var(--muted2);
  }}
  .empty {{
    padding: 28px;
    text-align: center;
    color: var(--muted);
    font-size: 0.85rem;
  }}
  .meta-strip {{
    display: flex;
    flex-wrap: wrap;
    gap: 10px 18px;
    margin-top: 6px;
    font-size: 0.58rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--muted2);
  }}
  .meta-strip b {{ color: var(--muted); font-weight: 600; }}
</style>
</head>
<body>
<div class="app">
  <div class="topline">
    <div class="brand"><span class="brand-dot"></span> Acid Bourse</div>
    <div class="clock">
      <span id="scanTime">{gen_short}</span>
      <svg class="wave" viewBox="0 0 48 16" fill="none" aria-hidden="true">
        <path d="M0 8 Q4 2 8 8 T16 8 T24 8 T32 8 T40 8 T48 8" stroke="rgba(200,240,74,0.5)" stroke-width="1.2"/>
      </svg>
    </div>
  </div>

  <div class="stage">
    <div class="rail-left">
      <p class="tagline">Intelligence layer<br/>for retail degenerates<br/>and market idiots.</p>
      <div class="title-stack">
        <h1>Idiot<br/><b>Flow</b></h1>
        <p class="title-sub">The market's too complex.<br/>Follow the flow.</p>
      </div>
      <ul class="nav-list">
        <li><a class="active" href="#overview">Overview</a></li>
        <li><a href="#signals">Signals</a></li>
        <li><a href="#board">Board</a></li>
        <li><a href="#teardown">Teardown</a></li>
        <li><a href="#audit">Audit</a></li>
      </ul>
      <div class="meta-strip">
        <span>{venue}</span>
        <span><b>{mode}</b></span>
        <span>{n_ideas} ideas · {n_raw} raw</span>
        <span>{n_ad} adaptive</span>
      </div>
    </div>

    <div class="orb-zone" id="overview">
      <div class="orb" id="heroOrb">
        <div class="orb-core" id="heroSignal">
          <div class="orb-label">Primary signal</div>
          <div class="empty" style="padding:12px;font-size:0.8rem">No potato signals this scan.</div>
        </div>
      </div>
      <div class="orb-bubble b1"></div>
      <div class="orb-bubble b2"></div>
      <div class="orb-ripple"></div>
    </div>

    <div class="rail-right">
      <div class="stat">
        <span class="k">Scan universe</span>
        <span class="v">{n_ideas}</span>
        <span class="s dim">IDEAS</span>
      </div>
      <div class="stat">
        <span class="k">Long board</span>
        <span class="v pos">{int(round(long_share*100))}%</span>
        <span class="s">SHARE</span>
      </div>
      <div class="stat">
        <span class="k">Short board</span>
        <span class="v {'neg' if short_share > 0 else ''}">{int(round(short_share*100))}%</span>
        <span class="s dim">SHARE</span>
      </div>
      <div class="stat">
        <span class="k">Flow volatility</span>
        <span class="v">{avg_z:.2f}</span>
        <span class="s warn">{vol_label}</span>
      </div>
      <div class="stat">
        <span class="k">Market breadth</span>
        <span class="v">{breadth} / 100</span>
        <span class="s">{breadth_label}</span>
      </div>
      <div class="stat">
        <span class="k">Board index</span>
        <span class="v">{alt_idx}</span>
        <span class="s dim">{alt_label}</span>
      </div>
      <div class="stat" style="display:none">
        <span class="k">Vol proxy</span>
        <span class="v">{total_vol_s}</span>
        <span class="s dim">24H ROLL</span>
      </div>
    </div>
  </div>

  <section class="projection" id="signals">
    <div class="proj-head">
      <h2>Flow projection</h2>
      <span class="hint">(board path · flat price)</span>
    </div>
    <div class="proj-chart" id="pathChart"></div>
    <div class="proj-foot">
      <span>Entry zone · <b id="pathTarget">—</b></span>
      <span>Time horizon: 0–{horizon}h</span>
    </div>
  </section>

  <section class="board-sec" id="board">
    <div class="board-head">
      <h2>The Board</h2>
      <span>Top opportunities</span>
    </div>
    <div class="board-orbs" id="ranked"></div>
  </section>

  <section class="lower" id="teardown">
    <div>
      <h3 class="sec-title">Signal teardown</h3>
      <div class="teardown-grid">
        <div class="radar-wrap" id="radar"></div>
        <div>
          <div class="td-head">
            <span class="sym" id="tdSym">—</span>
            <span class="side LONG" id="tdSide">—</span>
          </div>
          <div class="td-list" id="tdList"></div>
          <div class="overall">Overall conviction <b id="tdConv">—</b></div>
        </div>
      </div>
    </div>
    <div>
      <h3 class="sec-title">Regime</h3>
      <div class="td-head">
        <span class="sym" id="regimeTitle">{herd_bias}</span>
      </div>
      <p style="margin:0 0 14px;font-size:0.82rem;line-height:1.5;color:var(--ink2)" id="regimeCopy">{herd_note}</p>
      <div class="td-list">
        <div class="row"><span>Short-board</span><b id="shortShare">{int(round(short_share*100))}%</b></div>
        <div class="row"><span>Long-board</span><b class="pos" id="longShare">{int(round(long_share*100))}%</b></div>
        <div class="row"><span>Adaptive ready</span><b>{n_ad}</b></div>
        <div class="row"><span>Classic raw</span><b>{n_raw}</b></div>
        <div class="row"><span>Pressure</span><b class="hi" id="distLabel">{dist_label} {dist_pct}%</b></div>
      </div>
    </div>
    <div class="notes">
      <h3 class="sec-title">Notes to self</h3>
      <ul>
        <li>Don't marry a coin.</li>
        <li>Invalidation is survival.</li>
        <li>Let winners run.</li>
        <li>Size small. Sleep well.</li>
        <li>Trade safe. Stay liquid.</li>
      </ul>
      <div class="zen" aria-hidden="true">
        <div class="zen-rings"></div>
        <div class="zen-stone"></div>
        <svg class="zen-tree" viewBox="0 0 36 48" fill="none">
          <path d="M18 46 V28" stroke="#4a4a40" stroke-width="1.5"/>
          <ellipse cx="18" cy="18" rx="12" ry="14" fill="#3a4230" opacity="0.8"/>
          <ellipse cx="14" cy="14" rx="7" ry="8" fill="#4a5240" opacity="0.6"/>
        </svg>
      </div>
    </div>
  </section>

  <section class="audit" id="audit">
    <div class="board-head">
      <h2>Full-board audit</h2>
    </div>
    <div class="table-card">
      <div class="table-toolbar">
        <select id="sideFilter">
          <option value="ALL">All sides</option>
          <option value="LONG">Longs</option>
          <option value="SHORT">Shorts</option>
        </select>
        <select id="stateFilter">
          <option value="ALL">All states</option>
          <option value="READY" selected>Ready only</option>
          <option value="FILTERED">Filtered out</option>
          <option value="PATH">Path / other</option>
        </select>
        <select id="sortBy">
          <option value="score">Sort: score</option>
          <option value="strength">Sort: strength</option>
          <option value="delta">Sort: |Δ|</option>
          <option value="outz">Sort: z-out</option>
          <option value="att">Sort: attention</option>
          <option value="vol">Sort: volume</option>
        </select>
        <input id="minStr" type="number" value="0" step="1" placeholder="Min strength"/>
        <input id="minVol" type="number" value="0" step="10000" placeholder="Min vol"/>
        <button id="apply">Apply</button>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Score</th>
              <th>Strength</th>
              <th>State</th>
              <th>Symbol</th>
              <th>Side</th>
              <th>Δ (1h)</th>
              <th>Z-out</th>
              <th>Edge</th>
              <th>Attention</th>
              <th>RVOL</th>
              <th>Volume</th>
              <th>Path</th>
            </tr>
          </thead>
          <tbody id="tbody"></tbody>
        </table>
      </div>
    </div>
  </section>

  <footer class="foot">
    <div>
      <span class="logo">Acid Bourse Systems</span>
      &nbsp;·&nbsp; Ver 2.0.1
      <div class="inspire">
        Inspired by
        <a href="https://robotjames.substack.com/p/a-truly-idiotic-crypto-trade" target="_blank" rel="noopener">
          Robot James — A truly idiotic crypto trade
        </a>
        · independent tool, not affiliated
      </div>
    </div>
    <div class="live">Data stream: live</div>
    <div>Scan {elapsed}s · Not financial advice</div>
  </footer>
</div>

<script id="payload" type="application/json">{data_json}</script>
<script>
const DATA = JSON.parse(document.getElementById('payload').textContent);
let selected = 0;

function fmt(n, d=2) {{
  if (n === undefined || n === null || Number.isNaN(+n)) return '—';
  return Number(n).toFixed(d);
}}
function fmtVol(v) {{
  if (v == null) return '—';
  if (v >= 1e9) return '$' + (v/1e9).toFixed(2) + 'B';
  if (v >= 1e6) return '$' + (v/1e6).toFixed(2) + 'M';
  if (v >= 1e3) return '$' + (v/1e3).toFixed(1) + 'K';
  return '$' + String(Math.round(v));
}}
function cls(n) {{ return n >= 0 ? 'pos' : 'neg'; }}
function baseSym(s) {{
  return (s || '').replace('-USDT-SWAP','').replace('USDT','');
}}
function statePill(s) {{
  if (!s) return '';
  if (String(s).includes('READY')) return `<span class="pill ready">${{s}}</span>`;
  if (String(s).includes('FILTERED')) return `<span class="pill filtered">${{s}}</span>`;
  return `<span class="pill">${{s}}</span>`;
}}
function strengthBars(str) {{
  const n = Math.max(0, Math.min(5, Math.round((str || 0) / 20)));
  let h = '';
  for (let i = 0; i < 5; i++) h += `<i class="${{i < n ? 'on' : ''}}"></i>`;
  return `<span class="bars">${{h}}</span>`;
}}
function conviction(str) {{
  if (str >= 70) return {{ label: 'HIGH', cls: '' }};
  if (str >= 45) return {{ label: 'MED', cls: 'mid' }};
  return {{ label: 'LOW', cls: 'low' }};
}}
function metricWord(v, high, mid) {{
  if (v >= high) return 'STRONG';
  if (v >= mid) return 'SOLID';
  if (v > 0) return 'SOFT';
  return 'WEAK';
}}

function pathPoints(path) {{
  if (!path || path.length < 2) return null;
  const ys = path.map(p => p.displayed_24h_pct);
  const min = Math.min(...ys), max = Math.max(...ys);
  const span = (max - min) || 1;
  return {{ ys, min, max, span, path }};
}}

function sparkStep(path, w, h, color, fillBand) {{
  const pts = pathPoints(path);
  if (!pts) return '';
  const pad = 4;
  const n = pts.path.length;
  const coords = pts.path.map((p, i) => {{
    const x = pad + (i / (n - 1)) * (w - pad * 2);
    const y = pad + (1 - (p.displayed_24h_pct - pts.min) / pts.span) * (h - pad * 2);
    return [x, y];
  }});
  let d = `M${{coords[0][0]}},${{coords[0][1]}}`;
  for (let i = 1; i < coords.length; i++) {{
    d += ` H${{coords[i][0]}} V${{coords[i][1]}}`;
  }}
  let band = '';
  if (fillBand) {{
    const area = d + ` L${{coords.at(-1)[0]}},${{h - pad}} L${{coords[0][0]}},${{h - pad}} Z`;
    band = `<path d="${{area}}" fill="${{fillBand}}" opacity="0.15"/>`;
  }}
  let zero = '';
  if (pts.min <= 0 && pts.max >= 0) {{
    const y0 = pad + (1 - (0 - pts.min) / pts.span) * (h - pad * 2);
    zero = `<line x1="${{pad}}" y1="${{y0}}" x2="${{w - pad}}" y2="${{y0}}" stroke="rgba(255,255,255,0.1)" stroke-dasharray="3,3"/>`;
  }}
  return `<svg viewBox="0 0 ${{w}} ${{h}}" preserveAspectRatio="none">
    ${{zero}}${{band}}
    <path d="${{d}}" fill="none" stroke="${{color}}" stroke-width="2" stroke-linejoin="round"/>
  </svg>`;
}}

function bigPath(path, side) {{
  const pts = pathPoints(path);
  const w = 900, h = 150, padL = 16, padR = 48, padT = 28, padB = 24;
  if (!pts) return '<div class="empty">No path</div>';
  const n = pts.path.length;
  const isLong = side !== 'SHORT';
  const stroke = isLong ? '#c8f04a' : '#e84a9a';
  const glow = isLong ? 'rgba(200,240,74,0.25)' : 'rgba(232,74,154,0.25)';
  const coords = pts.path.map((p, i) => {{
    const x = padL + (i / (n - 1)) * (w - padL - padR);
    const y = padT + (1 - (p.displayed_24h_pct - pts.min) / pts.span) * (h - padT - padB);
    return [x, y, p];
  }});
  // smooth-ish polyline (step still conveys board path)
  let d = `M${{coords[0][0]}},${{coords[0][1]}}`;
  for (let i = 1; i < coords.length; i++) {{
    const mx = (coords[i-1][0] + coords[i][0]) / 2;
    d += ` C${{mx}},${{coords[i-1][1]}} ${{mx}},${{coords[i][1]}} ${{coords[i][0]}},${{coords[i][1]}}`;
  }}
  const area = d + ` L${{coords.at(-1)[0]}},${{h - padB}} L${{coords[0][0]}},${{h - padB}} Z`;
  // T markers at quartiles
  const marks = [0, 0.33, 0.66, 1].map((t, mi) => {{
    const i = Math.min(n - 1, Math.round(t * (n - 1)));
    const [x, y, p] = coords[i];
    const lab = 'T' + (mi + 1);
    const val = p.displayed_24h_pct.toFixed(2) + '%';
    return `
      <circle cx="${{x}}" cy="${{y}}" r="4" fill="${{stroke}}" stroke="#0a0b0e" stroke-width="1.5"/>
      <text x="${{x}}" y="${{y - 12}}" text-anchor="middle" fill="${{stroke}}" font-size="9" font-family="Inter,sans-serif" font-weight="600" letter-spacing="0.1em">${{lab}}</text>
      <text x="${{x}}" y="${{h - 6}}" text-anchor="middle" fill="rgba(200,196,186,0.55)" font-size="9" font-family="IBM Plex Mono,monospace">${{val}}</text>`;
  }}).join('');
  // invalidation dashed line
  const invY = padT + (1 - (pts.min - pts.min) / pts.span) * (h - padT - padB);
  return `<svg viewBox="0 0 ${{w}} ${{h}}" preserveAspectRatio="none">
    <defs>
      <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="${{stroke}}" stop-opacity="0.25"/>
        <stop offset="100%" stop-color="${{stroke}}" stop-opacity="0"/>
      </linearGradient>
      <filter id="glow"><feGaussianBlur stdDeviation="2.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    </defs>
    <line x1="${{padL}}" y1="${{h - padB}}" x2="${{w - padR}}" y2="${{h - padB}}" stroke="rgba(232,74,154,0.35)" stroke-dasharray="4,4"/>
    <path d="${{area}}" fill="url(#areaGrad)"/>
    <path d="${{d}}" fill="none" stroke="${{stroke}}" stroke-width="2.2" stroke-linejoin="round" filter="url(#glow)"/>
    ${{marks}}
  </svg>`;
}}

function radarSvg(i) {{
  // 5 axes: Momentum(strength), Liquidity(vol score), Sentiment(att), Structure(edge), Vol Accum(rvol)
  const str = Math.max(0, Math.min(100, i.strength_pine || i.score || 0));
  const liq = Math.max(0, Math.min(100, i.liquidity_score || 40));
  const sent = Math.max(0, Math.min(100, i.attention_rank || 40));
  const edge = Math.max(0, Math.min(100, (Math.abs(i.roll_edge_z || 0) / 3) * 100));
  const rvol = Math.max(0, Math.min(100, (i.rvol || 0) * 40));
  const vals = [str, liq, sent, edge, rvol];
  const labels = ['MOM', 'LIQ', 'SENT', 'EDGE', 'RVOL'];
  const cx = 65, cy = 65, R = 48;
  const n = 5;
  const pt = (v, k) => {{
    const a = -Math.PI / 2 + (k * 2 * Math.PI) / n;
    const r = (v / 100) * R;
    return [cx + r * Math.cos(a), cy + r * Math.sin(a)];
  }};
  const grid = [0.33, 0.66, 1].map(s => {{
    const pts = Array.from({{length: n}}, (_, k) => {{
      const a = -Math.PI / 2 + (k * 2 * Math.PI) / n;
      return `${{cx + R * s * Math.cos(a)}},${{cy + R * s * Math.sin(a)}}`;
    }}).join(' ');
    return `<polygon points="${{pts}}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="1"/>`;
  }}).join('');
  const axes = Array.from({{length: n}}, (_, k) => {{
    const a = -Math.PI / 2 + (k * 2 * Math.PI) / n;
    const x = cx + R * Math.cos(a), y = cy + R * Math.sin(a);
    const lx = cx + (R + 12) * Math.cos(a), ly = cy + (R + 12) * Math.sin(a);
    return `<line x1="${{cx}}" y1="${{cy}}" x2="${{x}}" y2="${{y}}" stroke="rgba(255,255,255,0.08)"/>
      <text x="${{lx}}" y="${{ly}}" text-anchor="middle" dominant-baseline="middle" fill="rgba(122,118,112,0.9)" font-size="7" font-family="Inter,sans-serif" font-weight="600">${{labels[k]}}</text>`;
  }}).join('');
  const poly = vals.map((v, k) => pt(v, k).join(',')).join(' ');
  return `<svg viewBox="0 0 130 130">
    ${{grid}}${{axes}}
    <polygon points="${{poly}}" fill="rgba(200,240,74,0.18)" stroke="#c8f04a" stroke-width="1.5"/>
    ${{vals.map((v, k) => {{
      const [x, y] = pt(v, k);
      return `<circle cx="${{x}}" cy="${{y}}" r="2.5" fill="#c8f04a"/>`;
    }}).join('')}}
  </svg>`;
}}

function listForRank() {{
  const pot = DATA.potato || [];
  if (pot.length) return pot;
  return (DATA.ideas || []).slice(0, 8);
}}

function renderHero(i) {{
  const el = document.getElementById('heroSignal');
  if (!i) {{
    el.innerHTML = '<div class="orb-label">Primary signal</div><div class="empty" style="padding:12px;font-size:0.8rem">No potato signals this scan.</div>';
    document.getElementById('pathChart').innerHTML = '<div class="empty">No path</div>';
    document.getElementById('pathTarget').textContent = '—';
    renderTeardown(null);
    return;
  }}
  const str = i.strength_pine || i.score || 0;
  const side = i.side || '—';
  const conv = conviction(str);
  const arrow = side === 'SHORT' ? '↓' : '↑';
  el.innerHTML = `
    <div class="orb-label">Primary signal</div>
    <h2 class="orb-sym">${{baseSym(i.symbol)}}<small>/USDT</small></h2>
    <div class="orb-side ${{side}}">${{side}} <span class="arrow">${{arrow}}</span></div>
    <div class="orb-score-label">Flow score</div>
    <div class="orb-score">${{Math.round(str)}}</div>
    <div class="orb-conv ${{conv.cls}}">Conviction: <b>${{conv.label}}</b></div>
  `;
  document.getElementById('pathChart').innerHTML = bigPath(i.path, side);
  document.getElementById('pathTarget').textContent =
    `${{fmt(i.current_24h_pct)}}% → ${{fmt(i.flat_next_24h_pct)}}%  (Δ ${{fmt(i.known_roll_delta_pp)}}pp)`;
  renderTeardown(i);
}}

function renderTeardown(i) {{
  if (!i) {{
    document.getElementById('tdSym').textContent = '—';
    document.getElementById('tdSide').textContent = '—';
    document.getElementById('tdList').innerHTML = '';
    document.getElementById('tdConv').textContent = '—';
    document.getElementById('radar').innerHTML = '';
    return;
  }}
  const str = i.strength_pine || i.score || 0;
  const side = i.side || '—';
  document.getElementById('tdSym').textContent = baseSym(i.symbol) + ' /USDT';
  const sideEl = document.getElementById('tdSide');
  sideEl.textContent = side;
  sideEl.className = 'side ' + side;
  document.getElementById('tdConv').textContent = conviction(str).label;
  document.getElementById('radar').innerHTML = radarSvg(i);
  const rows = [
    ['Shock z (out)', fmt(i.outgoing_z, 2), Math.abs(i.outgoing_z||0) >= 1.5 ? 'hi' : ''],
    ['Edge z', fmt(i.roll_edge_z, 2), Math.abs(i.roll_edge_z||0) >= 1.5 ? 'hi' : ''],
    ['Attention', fmt(i.attention_rank, 0) + 'p', (i.attention_rank||0) >= 70 ? 'hi' : ''],
    ['RVOL', fmt(i.rvol, 2) + 'x', (i.rvol||0) >= 1 ? 'hi' : ''],
    ['Δ board 1h', fmt(i.known_roll_delta_pp) + 'pp', cls(i.known_roll_delta_pp)],
    ['Setup', i.setup_state || '—', i.adaptive_pass ? 'hi' : ''],
    ['Volume', fmtVol(i.roll_volume), ''],
  ];
  document.getElementById('tdList').innerHTML = rows.map(([k, v, c]) =>
    `<div class="row"><span>${{k}}</span><b class="${{c}}">${{v}}</b></div>`
  ).join('');
}}

function renderRanked() {{
  const list = listForRank();
  const el = document.getElementById('ranked');
  if (!list.length) {{
    el.innerHTML = '<div class="empty" style="width:100%">No ranked opportunities.</div>';
    return;
  }}
  el.innerHTML = list.map((i, idx) => {{
    const str = Math.round(i.strength_pine || i.score || 0);
    const side = i.side || 'LONG';
    const vol = i.known_roll_delta_pp != null
      ? ((i.known_roll_delta_pp >= 0 ? '+' : '') + fmt(i.known_roll_delta_pp) + 'pp')
      : fmtVol(i.roll_volume);
    return `
    <article class="token-orb ${{side}} ${{idx === selected ? 'active' : ''}}" data-idx="${{idx}}">
      <div class="orb-ball">
        <span class="idx">${{String(idx + 1).padStart(2,'0')}}</span>
        <div>
          <div class="sym">${{baseSym(i.symbol)}}</div>
          <div class="sc">${{str}}</div>
        </div>
      </div>
      <div class="vol">${{vol}}</div>
      <div class="reflect"></div>
    </article>`;
  }}).join('');
  el.querySelectorAll('.token-orb').forEach(card => {{
    card.addEventListener('click', () => {{
      selected = +card.dataset.idx;
      renderRanked();
      renderHero(list[selected]);
    }});
  }});
}}

function filteredIdeas() {{
  const side = document.getElementById('sideFilter').value;
  const state = document.getElementById('stateFilter').value;
  const sortBy = document.getElementById('sortBy').value;
  const minStr = Number(document.getElementById('minStr').value || 0);
  const minVol = Number(document.getElementById('minVol').value || 0);
  let rows = (DATA.ideas || []).filter(i => {{
    if ((i.strength_pine || 0) < minStr) return false;
    if ((i.roll_volume || 0) < minVol) return false;
    if (side !== 'ALL' && i.side !== side) return false;
    const st = i.setup_state || '';
    if (state === 'READY' && !st.includes('READY')) return false;
    if (state === 'FILTERED' && !st.includes('FILTERED')) return false;
    if (state === 'PATH' && (st.includes('READY') || st.includes('FILTERED'))) return false;
    return true;
  }});
  const key = {{
    score: i => i.score,
    strength: i => i.strength_pine || 0,
    delta: i => Math.abs(i.known_roll_delta_pp || 0),
    outz: i => i.outgoing_z || 0,
    att: i => i.attention_rank || 0,
    vol: i => i.roll_volume || 0,
  }}[sortBy];
  rows.sort((a, b) => {{
    const ap = a.adaptive_pass ? 1 : 0, bp = b.adaptive_pass ? 1 : 0;
    if (bp !== ap) return bp - ap;
    return key(b) - key(a);
  }});
  return rows;
}}

function renderTable() {{
  const rows = filteredIdeas();
  const tb = document.getElementById('tbody');
  if (!rows.length) {{
    tb.innerHTML = '<tr><td colspan="12" class="empty">No rows match these filters. Try “All states”.</td></tr>';
    return;
  }}
  const stroke = '#c8f04a';
  tb.innerHTML = rows.map(i => `
    <tr>
      <td class="score">${{Math.round(i.strength_pine || i.score || 0)}}</td>
      <td>${{strengthBars(i.strength_pine || 0)}}</td>
      <td>${{statePill(i.setup_state)}}</td>
      <td class="sym">${{i.symbol}}</td>
      <td><span class="pill ${{(i.side || '').toLowerCase()}}">${{i.side}}</span></td>
      <td class="${{cls(i.known_roll_delta_pp)}}">${{fmt(i.known_roll_delta_pp)}}%</td>
      <td>${{fmt(i.outgoing_z,2)}}</td>
      <td>${{fmt(i.roll_edge_z,2)}} / ${{fmt(i.outgoing_z,2)}}</td>
      <td>${{fmt(i.attention_rank,0)}}p / ${{fmt(i.rvol,2)}}x</td>
      <td>${{fmt(i.rvol,2)}}x</td>
      <td>${{fmtVol(i.roll_volume)}}</td>
      <td class="path-cell">${{sparkStep(i.path, 72, 28, i.side === 'SHORT' ? '#e84a9a' : stroke)}}</td>
    </tr>
  `).join('');
}}

document.getElementById('apply').onclick = renderTable;
['sideFilter','stateFilter','sortBy','minStr','minVol'].forEach(id => {{
  document.getElementById(id).addEventListener('change', renderTable);
}});

const rankList = listForRank();
renderHero(rankList[0]);
renderRanked();
const hasReady = (DATA.ideas || []).some(i => (i.setup_state || '').includes('READY'));
if (!hasReady) document.getElementById('stateFilter').value = 'ALL';
renderTable();
</script>
</body>
</html>
"""
    out_path = Path(out_path)
    out_path.write_text(html, encoding="utf-8")
    return out_path
