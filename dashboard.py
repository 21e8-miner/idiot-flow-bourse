#!/usr/bin/env python3
"""
Generate Idiot Flow Lab HTML ΓÇö exact match to rj new style.png
(Acid Bourse ┬╖ dark cinematic glass ┬╖ mobile-perfect).
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


def _fmt_flow(v: float, signed: bool = False, neg: bool = False) -> str:
    sign = ""
    if neg and v:
        sign = "-"
    elif signed and v:
        sign = "+"
    av = abs(v)
    if av >= 1e9:
        return f"{sign}${av/1e9:.2f}B"
    if av >= 1e6:
        return f"{sign}${av/1e6:.2f}M"
    if av >= 1e3:
        return f"{sign}${av/1e3:.1f}K"
    if av <= 0:
        return f"{sign}$0"
    return f"{sign}${av:.0f}"


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
    gen_display = generated.upper().replace(" UTC", " EST") if generated else "ΓÇö"
    venue = _esc(str(meta.get("venue_label") or meta.get("venue", "")))
    mode = _esc(str(meta.get("mode", "adaptive")).title())
    n_ad = meta.get("n_adaptive", herd.get("n_adaptive", 0))
    n_raw = meta.get("n_classic_raw", 0)
    n_ideas = meta.get("n_ideas", len(ideas))
    long_share = float(herd.get("long_share") or 0.5)
    short_share = float(herd.get("short_share") or 0.5)
    elapsed = meta.get("elapsed_s", 0)
    horizon = meta.get("horizon", 12)
    median_score = float(meta.get("median_score") or 0)

    total_vol = sum(float(i.get("roll_volume") or 0) for i in ideas)
    long_vol = sum(float(i.get("roll_volume") or 0) for i in ideas if i.get("side") == "LONG")
    short_vol = sum(float(i.get("roll_volume") or 0) for i in ideas if i.get("side") == "SHORT")
    zs = [abs(float(i.get("outgoing_z") or 0)) for i in ideas]
    avg_z = sum(zs) / len(zs) if zs else 0.0
    vol_label = "ELEVATED" if avg_z >= 1.5 else ("ACTIVE" if avg_z >= 0.8 else "CALM")
    breadth = int(round(long_share * 100))
    breadth_label = (
        "EXPANDING" if long_share >= 0.55 else ("CONTRACTING" if long_share <= 0.45 else "NEUTRAL")
    )
    alt_idx = max(0, min(100, int(round(median_score * 2.2)) if median_score else 50))
    alt_label = "BULLISH" if alt_idx >= 60 else ("BEARISH" if alt_idx <= 40 else "NEUTRAL")

    total_s = _fmt_flow(total_vol, signed=True)
    long_s = _fmt_flow(long_vol, signed=True)
    short_s = _fmt_flow(short_vol, neg=True)

    # uptime-ish display from elapsed
    try:
        es = float(elapsed)
        um, us = divmod(int(es), 60)
        uptime = f"{um}M {us:02d}S SCAN"
    except (TypeError, ValueError):
        uptime = "ΓÇö"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"/>
<meta name="theme-color" content="#050608"/>
<meta name="apple-mobile-web-app-capable" content="yes"/>
<title>Idiot Flow ┬╖ Acid Bourse</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Inter:wght@200;300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet"/>
<style>
/* ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
   ACID BOURSE ΓÇö advanced RJ cinematic glass
   ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ */
:root {{
  --ink: #f7f3ea;
  --ink2: #d0c9bb;
  --muted: #918b7f;
  --muted2: #5e5a50;
  --lime: #c8f23a;
  --lime-dim: #9fc72a;
  --lime-hot: #e8ff6a;
  --lime-glow: rgba(200,242,58,0.5);
  --magenta: #f04a9e;
  --magenta-glow: rgba(240,74,158,0.48);
  --gold: #e0c078;
  --gold-glow: rgba(224,192,120,0.38);
  --line: rgba(255,255,255,0.07);
  --line2: rgba(255,255,255,0.13);
  --display: "Syne", "Inter", system-ui, sans-serif;
  --sans: "Inter", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
  --mono: "JetBrains Mono", ui-monospace, monospace;
  --safe-t: env(safe-area-inset-top, 0px);
  --safe-b: env(safe-area-inset-bottom, 0px);
  --safe-l: env(safe-area-inset-left, 0px);
  --safe-r: env(safe-area-inset-right, 0px);
  --pad-x: clamp(16px, 3.5vw, 48px);
  --max: 1280px;
}}
*, *::before, *::after {{ box-sizing: border-box; }}
html {{
  -webkit-text-size-adjust: 100%;
  scroll-behavior: smooth;
}}
html, body {{ margin: 0; padding: 0; }}
body {{
  font-family: var(--sans);
  color: var(--ink);
  min-height: 100dvh;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  overflow-x: hidden;
  background-color: #050608;
  background-image:
    radial-gradient(ellipse 90% 80% at 0% 0%, rgba(230,190,120,0.34) 0%, transparent 52%),
    radial-gradient(ellipse 55% 48% at 100% 4%, rgba(110,40,95,0.2) 0%, transparent 48%),
    radial-gradient(ellipse 70% 50% at 48% 100%, rgba(28,55,38,0.22) 0%, transparent 55%),
    radial-gradient(ellipse 40% 30% at 55% 40%, rgba(200,242,58,0.04) 0%, transparent 60%),
    linear-gradient(168deg, #1a1610 0%, #0c0d11 36%, #07080b 72%, #040506 100%);
  background-attachment: fixed;
}}
a {{ color: var(--lime); text-decoration: none; }}
button, select, input {{ font: inherit; color: inherit; }}
img, svg {{ max-width: 100%; display: block; }}

/* shell */
.shell {{
  width: 100%;
  max-width: var(--max);
  margin: 0 auto;
  padding:
    calc(18px + var(--safe-t))
    calc(var(--pad-x) + var(--safe-r))
    calc(28px + var(--safe-b))
    calc(var(--pad-x) + var(--safe-l));
}}

/* ΓöÇΓöÇ top bar ΓöÇΓöÇ */
.topline {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: clamp(18px, 3vw, 28px);
}}
.brand {{
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 0.625rem;
  font-weight: 600;
  letter-spacing: 0.28em;
  text-transform: uppercase;
  color: rgba(244,241,234,0.78);
}}
.brand-mark {{
  width: 14px; height: 14px;
  position: relative;
  flex-shrink: 0;
}}
.brand-mark span {{
  position: absolute;
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--lime);
  box-shadow: 0 0 8px var(--lime-glow);
}}
.brand-mark span:nth-child(1) {{ top: 0; left: 4px; }}
.brand-mark span:nth-child(2) {{ bottom: 0; left: 0; background: #a8d840; }}
.brand-mark span:nth-child(3) {{ bottom: 0; right: 0; background: #d4ef6a; }}
.clock {{
  display: flex;
  align-items: center;
  gap: 12px;
  font-family: var(--mono);
  font-size: 0.6rem;
  letter-spacing: 0.16em;
  color: var(--muted);
  text-transform: uppercase;
  white-space: nowrap;
}}
.wave {{
  width: 42px; height: 14px;
  opacity: 0.55;
  flex-shrink: 0;
}}

/* ΓöÇΓöÇ hero stage: left | orb | right ΓöÇΓöÇ */
.stage {{
  display: grid;
  grid-template-columns: minmax(140px, 1fr) minmax(240px, 1.45fr) minmax(140px, 1fr);
  gap: clamp(12px, 2.5vw, 28px);
  align-items: center;
  min-height: clamp(320px, 42vw, 440px);
}}

/* left column */
.col-left {{
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
  padding-top: 8px;
}}
.eyebrow {{
  margin: 0 0 22px;
  font-size: 0.58rem;
  font-weight: 500;
  letter-spacing: 0.18em;
  line-height: 1.65;
  text-transform: uppercase;
  color: var(--muted);
  max-width: 13rem;
}}
.eyebrow::after {{
  content: "";
  display: block;
  width: 16px;
  height: 1px;
  margin-top: 14px;
  background: rgba(255,255,255,0.18);
}}
.wordmark {{
  margin: 0;
  font-family: var(--display);
  font-weight: 500;
  font-size: clamp(2.15rem, 4.8vw, 3.45rem);
  line-height: 0.9;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ink);
  text-shadow: 0 0 40px rgba(247,243,234,0.08);
}}
.wordmark b {{
  font-weight: 700;
  display: block;
}}
.tagline {{
  margin: 18px 0 0;
  font-size: 0.58rem;
  font-weight: 500;
  letter-spacing: 0.16em;
  line-height: 1.55;
  text-transform: uppercase;
  color: var(--muted);
  max-width: 12rem;
}}
.tagline::after {{
  content: "";
  display: block;
  width: 16px;
  height: 1px;
  margin-top: 14px;
  background: rgba(255,255,255,0.18);
}}
.nav {{
  list-style: none;
  margin: 32px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 13px;
}}
.nav a {{
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-size: 0.62rem;
  font-weight: 500;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--muted);
  text-decoration: none;
  transition: color 0.15s;
  min-height: 28px;
}}
.nav a:hover {{ color: var(--ink2); }}
.nav a.on {{
  color: var(--lime);
}}
.nav a.on::before {{
  content: "";
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--lime);
  box-shadow: 0 0 10px var(--lime-glow);
  flex-shrink: 0;
}}

/* center glass blob */
.col-orb {{
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 0;
  padding: 8px 0 36px;
}}
.blob {{
  --s: min(340px, 78vw);
  width: var(--s);
  height: var(--s);
  position: relative;
  display: grid;
  place-items: center;
  isolation: isolate;
  animation: floaty 9s ease-in-out infinite;
}}
@keyframes floaty {{
  0%, 100% {{ transform: translateY(0); }}
  50% {{ transform: translateY(-8px); }}
}}
.blob-ribbon {{
  position: absolute;
  inset: -8%;
  border-radius: 48% 52% 47% 53% / 53% 47% 53% 47%;
  background:
    conic-gradient(from 200deg at 50% 50%,
      transparent 0deg,
      rgba(224,192,120,0.55) 40deg,
      rgba(200,242,58,0.35) 80deg,
      transparent 120deg,
      rgba(240,74,158,0.4) 200deg,
      rgba(120,180,255,0.25) 250deg,
      transparent 300deg,
      rgba(224,192,120,0.45) 340deg,
      transparent 360deg);
  filter: blur(14px) saturate(1.3);
  opacity: 0.85;
  animation: ribbon 14s linear infinite, morph 10s ease-in-out infinite;
  z-index: 0;
  pointer-events: none;
}}
@keyframes ribbon {{
  to {{ transform: rotate(360deg); }}
}}
.blob-shape {{
  position: absolute;
  inset: 0;
  border-radius: 48% 52% 47% 53% / 53% 47% 53% 47%;
  background:
    radial-gradient(ellipse 48% 42% at 32% 28%, rgba(255,255,255,0.78) 0%, transparent 42%),
    radial-gradient(ellipse 38% 34% at 72% 24%, rgba(255,130,210,0.58) 0%, transparent 48%),
    radial-gradient(ellipse 42% 40% at 22% 68%, rgba(200,242,58,0.48) 0%, transparent 50%),
    radial-gradient(ellipse 50% 44% at 78% 72%, rgba(100,170,230,0.38) 0%, transparent 52%),
    radial-gradient(ellipse 55% 50% at 55% 55%, rgba(224,192,120,0.12) 0%, transparent 60%),
    radial-gradient(ellipse 70% 70% at 50% 50%, rgba(40,48,55,0.35) 0%, rgba(8,10,14,0.6) 100%);
  box-shadow:
    0 0 0 1px rgba(255,255,255,0.22) inset,
    0 0 0 1px rgba(255,255,255,0.06),
    0 0 60px rgba(200,242,58,0.16),
    0 0 100px rgba(240,74,158,0.12),
    0 0 80px rgba(224,192,120,0.1),
    0 50px 100px rgba(0,0,0,0.55);
  filter: saturate(1.2);
  animation: morph 10s ease-in-out infinite;
  z-index: 1;
}}
@keyframes morph {{
  0%, 100% {{ border-radius: 48% 52% 47% 53% / 53% 47% 53% 47%; }}
  33% {{ border-radius: 53% 47% 52% 48% / 48% 54% 46% 52%; }}
  66% {{ border-radius: 46% 54% 50% 50% / 54% 46% 54% 46%; }}
}}
.blob-glass {{
  position: absolute;
  inset: 7%;
  border-radius: 48% 52% 47% 53% / 53% 47% 53% 47%;
  background:
    radial-gradient(ellipse 80% 70% at 50% 48%, rgba(6,8,12,0.38) 0%, rgba(4,6,10,0.82) 100%);
  box-shadow:
    0 0 40px rgba(0,0,0,0.4) inset,
    0 0 0 1px rgba(255,255,255,0.07) inset;
  animation: morph 10s ease-in-out infinite;
  backdrop-filter: blur(2px);
  z-index: 2;
}}
.blob-shine {{
  position: absolute;
  width: 36%;
  height: 20%;
  top: 10%;
  left: 18%;
  border-radius: 50%;
  background: linear-gradient(180deg, rgba(255,255,255,0.72), transparent);
  filter: blur(7px);
  pointer-events: none;
  z-index: 3;
}}
.blob-shine2 {{
  position: absolute;
  width: 20%;
  height: 12%;
  top: 20%;
  right: 20%;
  border-radius: 50%;
  background: linear-gradient(180deg, rgba(255,190,230,0.45), transparent);
  filter: blur(5px);
  pointer-events: none;
  z-index: 3;
}}
.blob-core {{
  position: relative;
  z-index: 4;
  text-align: center;
  padding: 20px 28px;
  width: 78%;
}}
.blob-lbl {{
  font-size: 0.55rem;
  font-weight: 600;
  letter-spacing: 0.34em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 10px;
}}
.blob-sym {{
  margin: 0;
  font-family: var(--display);
  font-size: clamp(1.9rem, 5.6vw, 2.85rem);
  font-weight: 600;
  letter-spacing: 0.14em;
  line-height: 1;
  color: var(--ink);
  text-transform: uppercase;
}}
.blob-pair {{
  display: block;
  margin-top: 6px;
  font-size: 0.68rem;
  font-weight: 500;
  letter-spacing: 0.3em;
  color: var(--muted);
}}
.blob-live {{
  margin: 10px 0 0;
  font-family: var(--mono);
  font-size: 0.72rem;
  font-weight: 500;
  letter-spacing: 0.04em;
  color: var(--ink2);
  min-height: 1.2em;
  transition: color 0.15s ease, text-shadow 0.15s ease;
}}
.blob-live .px {{ color: var(--ink); }}
.blob-live .chg {{ margin-left: 8px; font-size: 0.68rem; }}
.blob-live .chg.up {{ color: var(--lime); }}
.blob-live .chg.dn {{ color: var(--magenta); }}
.blob-live.flash-up .px {{ color: var(--lime-hot); text-shadow: 0 0 14px var(--lime-glow); }}
.blob-live.flash-dn .px {{ color: var(--magenta); text-shadow: 0 0 14px var(--magenta-glow); }}
.blob-side {{
  margin: 12px 0 14px;
  font-family: var(--display);
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: 0.22em;
  text-transform: uppercase;
}}
.blob-side.LONG {{ color: var(--lime); text-shadow: 0 0 24px var(--lime-glow); }}
.blob-side.SHORT {{ color: var(--magenta); text-shadow: 0 0 24px var(--magenta-glow); }}
.blob-side .arr {{ font-weight: 500; margin-left: 2px; }}
.blob-score-lbl {{
  font-size: 0.55rem;
  font-weight: 600;
  letter-spacing: 0.28em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 2px;
}}
.blob-score {{
  font-family: var(--display);
  font-size: clamp(2.9rem, 8.2vw, 3.75rem);
  font-weight: 500;
  letter-spacing: -0.02em;
  line-height: 1;
  color: var(--ink);
}}
.blob-conv {{
  margin-top: 8px;
  font-size: 0.58rem;
  font-weight: 600;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted);
}}
.blob-conv b {{ color: var(--lime); font-weight: 700; }}
.blob-conv.mid b {{ color: var(--gold); }}
.blob-conv.low b {{ color: var(--muted); }}

/* droplets + reflection pool */
.drop {{
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
  z-index: 2;
  background:
    radial-gradient(circle at 35% 30%, rgba(255,255,255,0.7), rgba(180,220,80,0.25) 55%, transparent 70%);
  box-shadow: 0 0 10px rgba(198,239,58,0.25);
}}
.drop.d1 {{ width: 16px; height: 16px; right: 6%; bottom: 26%; opacity: 0.75; }}
.drop.d2 {{ width: 9px; height: 9px; left: 10%; bottom: 36%; opacity: 0.55; }}
.drop.d3 {{ width: 7px; height: 7px; right: 18%; bottom: 18%; opacity: 0.4; }}
.pool {{
  position: absolute;
  bottom: -6px;
  left: 50%;
  transform: translateX(-50%);
  width: 78%;
  height: 36px;
  pointer-events: none;
}}
.pool i {{
  position: absolute;
  left: 50%;
  top: 50%;
  border-radius: 50%;
  border: 1px solid rgba(255,255,255,0.07);
  transform: translate(-50%, -50%);
}}
.pool i:nth-child(1) {{ width: 100%; height: 100%; }}
.pool i:nth-child(2) {{ width: 122%; height: 130%; opacity: 0.7; }}
.pool i:nth-child(3) {{ width: 145%; height: 165%; opacity: 0.45; }}
.pool-glow {{
  position: absolute;
  left: 50%;
  bottom: 4px;
  transform: translateX(-50%);
  width: 55%;
  height: 18px;
  background: radial-gradient(ellipse, rgba(198,239,58,0.12), transparent 70%);
  filter: blur(4px);
  pointer-events: none;
}}

/* right stats */
.col-stats {{
  display: flex;
  flex-direction: column;
  gap: clamp(16px, 2.2vw, 22px);
  justify-content: center;
  text-align: right;
  min-width: 0;
  padding-top: 4px;
}}
.stat .k {{
  display: block;
  font-size: 0.55rem;
  font-weight: 600;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 3px;
}}
.stat .v {{
  display: block;
  font-family: var(--mono);
  font-size: clamp(1.05rem, 2.2vw, 1.35rem);
  font-weight: 500;
  letter-spacing: -0.02em;
  color: var(--ink);
  line-height: 1.15;
}}
.stat .v.pos {{ color: var(--lime); }}
.stat .v.neg {{ color: var(--magenta); }}
.stat .s {{
  display: block;
  margin-top: 2px;
  font-size: 0.55rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--lime);
}}
.stat .s.dim {{ color: var(--muted); }}
.stat .s.warn {{ color: var(--gold); }}

/* ΓöÇΓöÇ flow projection ΓöÇΓöÇ */
.projection {{
  margin-top: clamp(8px, 2vw, 18px);
  padding-top: 4px;
}}
.proj-head {{
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}}
.proj-head h2 {{
  margin: 0;
  font-size: 0.58rem;
  font-weight: 600;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--muted);
}}
.proj-head .sub {{
  font-size: 0.52rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted2);
}}
.proj-head .info {{
  width: 12px; height: 12px;
  border-radius: 50%;
  border: 1px solid rgba(255,255,255,0.2);
  font-size: 0.5rem;
  display: grid;
  place-items: center;
  color: var(--muted2);
  flex-shrink: 0;
}}
.proj-chart {{
  width: 100%;
  height: clamp(120px, 22vw, 160px);
  position: relative;
}}
.proj-chart svg {{ width: 100%; height: 100%; overflow: visible; }}
.proj-foot {{
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 4px;
  font-size: 0.52rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted2);
}}
.proj-foot b {{ color: var(--muted); font-weight: 500; }}

/* ΓöÇΓöÇ the board ΓöÇΓöÇ */
.board {{
  margin-top: clamp(28px, 4vw, 42px);
}}
.board-head {{
  display: flex;
  align-items: baseline;
  gap: 14px;
  margin-bottom: 16px;
}}
.board-head h2 {{
  margin: 0;
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--ink2);
}}
.board-head .sub {{
  font-size: 0.55rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted);
}}
.board-head .info {{
  width: 12px; height: 12px;
  border-radius: 50%;
  border: 1px solid rgba(255,255,255,0.2);
  font-size: 0.5rem;
  display: inline-grid;
  place-items: center;
  color: var(--muted2);
}}
.board-track {{
  display: flex;
  gap: clamp(14px, 2.5vw, 22px);
  overflow-x: auto;
  overflow-y: hidden;
  padding: 8px 2px 20px;
  scroll-snap-type: x mandatory;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  mask-image: linear-gradient(90deg, #000 0%, #000 calc(100% - 28px), transparent 100%);
  -webkit-mask-image: linear-gradient(90deg, #000 0%, #000 calc(100% - 28px), transparent 100%);
}}
.board-track::-webkit-scrollbar {{ display: none; }}
.token {{
  flex: 0 0 auto;
  width: 96px;
  scroll-snap-align: start;
  text-align: center;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: transform 0.18s ease;
}}
.token:active {{ transform: scale(0.97); }}
.token:hover {{ transform: translateY(-3px); }}
.sphere {{
  width: 88px;
  height: 88px;
  margin: 0 auto;
  border-radius: 50%;
  position: relative;
  display: grid;
  place-items: center;
  background:
    radial-gradient(circle at 32% 26%, rgba(255,255,255,0.78) 0%, transparent 36%),
    radial-gradient(circle at 70% 72%, rgba(0,0,0,0.28) 0%, transparent 48%),
    radial-gradient(circle at 50% 55%, rgba(180,230,45,0.82) 0%, rgba(45,65,10,0.96) 100%);
  box-shadow:
    0 0 0 1px rgba(255,255,255,0.24) inset,
    0 14px 28px rgba(0,0,0,0.45),
    0 0 28px rgba(200,242,58,0.28);
}}
.token.SHORT .sphere {{
  background:
    radial-gradient(circle at 32% 26%, rgba(255,255,255,0.78) 0%, transparent 36%),
    radial-gradient(circle at 70% 72%, rgba(0,0,0,0.28) 0%, transparent 48%),
    radial-gradient(circle at 50% 55%, rgba(240,74,158,0.82) 0%, rgba(70,16,42,0.96) 100%);
  box-shadow:
    0 0 0 1px rgba(255,255,255,0.2) inset,
    0 14px 28px rgba(0,0,0,0.4),
    0 0 24px rgba(232,67,154,0.22);
}}
.token.on .sphere {{
  box-shadow:
    0 0 0 1px rgba(255,255,255,0.38) inset,
    0 0 0 2px rgba(200,242,58,0.42),
    0 16px 32px rgba(0,0,0,0.48),
    0 0 36px var(--lime-glow);
}}
.token.SHORT.on .sphere {{
  box-shadow:
    0 0 0 1px rgba(255,255,255,0.38) inset,
    0 0 0 2px rgba(240,74,158,0.45),
    0 16px 32px rgba(0,0,0,0.48),
    0 0 36px var(--magenta-glow);
}}
.sphere .idx {{
  position: absolute;
  top: 11px;
  left: 0; right: 0;
  font-family: var(--mono);
  font-size: 0.52rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: rgba(255,255,255,0.55);
}}
.sphere .sym {{
  font-family: var(--display);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: #fff;
  text-shadow: 0 1px 4px rgba(0,0,0,0.45);
  margin-top: 8px;
  max-width: 76px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}}
.sphere .sc {{
  font-family: var(--display);
  font-size: 1.2rem;
  font-weight: 600;
  color: #fff;
  letter-spacing: -0.02em;
  line-height: 1;
  text-shadow: 0 1px 4px rgba(0,0,0,0.45);
}}
.token .flow {{
  margin-top: 8px;
  font-family: var(--mono);
  font-size: 0.6rem;
  font-weight: 500;
  color: var(--lime);
}}
.token.SHORT .flow {{ color: var(--magenta); }}
.token .live-px {{
  margin-top: 3px;
  font-family: var(--mono);
  font-size: 0.52rem;
  font-weight: 500;
  letter-spacing: 0.02em;
  color: var(--ink2);
  min-height: 1em;
  transition: color 0.12s ease;
}}
.token .live-px.up {{ color: var(--lime); }}
.token .live-px.dn {{ color: var(--magenta); }}
.token .live-chg {{
  font-family: var(--mono);
  font-size: 0.48rem;
  color: var(--muted);
  margin-top: 1px;
}}
.token .live-chg.up {{ color: var(--lime-dim); }}
.token .live-chg.dn {{ color: var(--magenta); }}
.token .mirror {{
  width: 64%;
  height: 9px;
  margin: 7px auto 0;
  border-radius: 50%;
  background: radial-gradient(ellipse, rgba(198,239,58,0.22), transparent 70%);
  filter: blur(2px);
}}
.token.SHORT .mirror {{
  background: radial-gradient(ellipse, rgba(232,67,154,0.22), transparent 70%);
}}
.token .arrow {{
  margin-top: 2px;
  font-size: 0.7rem;
  color: var(--lime);
  opacity: 0.7;
  line-height: 1;
}}
.token.SHORT .arrow {{ color: var(--magenta); }}

/* ΓöÇΓöÇ lower: teardown + notes ΓöÇΓöÇ */
.lower {{
  display: grid;
  grid-template-columns: 1.35fr 0.9fr;
  gap: clamp(20px, 4vw, 48px);
  margin-top: clamp(24px, 3.5vw, 36px);
  padding-top: clamp(20px, 3vw, 28px);
  border-top: 1px solid var(--line);
  align-items: start;
}}
.sec-lbl {{
  margin: 0 0 16px;
  font-size: 0.58rem;
  font-weight: 600;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--muted);
}}
.teardown {{
  display: grid;
  grid-template-columns: minmax(120px, 140px) 1fr;
  gap: clamp(14px, 2.5vw, 28px);
  align-items: center;
}}
.radar {{ width: 100%; max-width: 140px; aspect-ratio: 1; }}
.radar svg {{ width: 100%; height: 100%; }}
.td-head {{
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 10px 14px;
  margin-bottom: 12px;
}}
.td-head .sym {{
  font-size: 0.95rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--ink);
}}
.td-head .side {{
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.18em;
}}
.td-head .side.LONG {{ color: var(--lime); }}
.td-head .side.SHORT {{ color: var(--magenta); }}
.td-rows {{
  display: flex;
  flex-direction: column;
  gap: 5px;
}}
.td-rows .row {{
  display: flex;
  justify-content: space-between;
  gap: 16px;
  font-size: 0.72rem;
  color: var(--muted);
  line-height: 1.4;
}}
.td-rows .row b {{
  font-family: var(--mono);
  font-size: 0.68rem;
  font-weight: 600;
  color: var(--ink2);
  text-align: right;
}}
.td-rows .row b.hi {{ color: var(--lime); }}
.td-rows .row b.neg {{ color: var(--magenta); }}
.overall {{
  margin-top: 14px;
  font-size: 0.62rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
}}
.overall b {{ color: var(--lime); }}

/* notes + zen */
.notes-block {{ position: relative; min-height: 160px; }}
.notes-list {{
  margin: 0;
  padding: 0 0 0 1.1em;
  font-size: 0.78rem;
  line-height: 1.7;
  color: var(--ink2);
}}
.notes-list li {{ margin-bottom: 2px; }}
.notes-list li::marker {{ color: var(--muted2); font-size: 0.65em; }}
.zen {{
  position: absolute;
  right: 0;
  bottom: 0;
  width: min(200px, 48vw);
  height: 120px;
  pointer-events: none;
  opacity: 0.95;
}}
.zen-sand {{
  position: absolute;
  inset: 20% 0 0;
  border-radius: 50% 50% 40% 40%;
  background:
    radial-gradient(ellipse 60% 40% at 50% 40%, rgba(90,85,75,0.35), transparent 70%),
    linear-gradient(180deg, transparent, rgba(50,48,42,0.25));
}}
.zen-ring {{
  position: absolute;
  left: 42%;
  top: 52%;
  width: 70px; height: 38px;
  border-radius: 50%;
  border: 1px solid rgba(255,255,255,0.07);
  transform: translate(-50%, -50%);
  box-shadow:
    0 0 0 7px rgba(255,255,255,0.025),
    0 0 0 14px rgba(255,255,255,0.018),
    0 0 0 21px rgba(255,255,255,0.012);
}}
.zen-stone {{
  position: absolute;
  left: 42%;
  top: 50%;
  width: 20px; height: 14px;
  border-radius: 50%;
  background: radial-gradient(circle at 40% 35%, #6e6a60, #2a2824 70%);
  box-shadow: 0 3px 8px rgba(0,0,0,0.45);
  transform: translate(-50%, -50%);
}}
.zen-tree {{
  position: absolute;
  right: 8%;
  top: 8%;
  width: 52px;
  height: 64px;
  opacity: 0.7;
}}

/* ΓöÇΓöÇ Photon FSQ fingerprint ΓöÇΓöÇ */
.photon {{
  margin: clamp(28px, 4vw, 40px) 0;
  padding: 18px 18px 16px;
  border-radius: 18px;
  border: 1px solid var(--line2);
  background:
    radial-gradient(ellipse 80% 60% at 0% 0%, rgba(200,242,58,0.06), transparent 55%),
    radial-gradient(ellipse 50% 40% at 100% 100%, rgba(240,74,158,0.06), transparent 50%),
    rgba(255,255,255,0.02);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}}
.photon-head {{
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px 16px;
  margin-bottom: 14px;
}}
.photon-head h2 {{
  margin: 0;
  font-family: var(--display);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--ink);
}}
.photon-head h2 em {{
  font-style: normal;
  color: var(--lime);
}}
.photon-head .sub {{
  font-size: 0.68rem;
  color: var(--muted);
  max-width: 36rem;
  line-height: 1.4;
}}
.photon-grid-wrap {{
  display: grid;
  grid-template-columns: 1.4fr 0.9fr;
  gap: 14px;
}}
@media (max-width: 820px) {{
  .photon-grid-wrap {{ grid-template-columns: 1fr; }}
}}
.photon-lattice {{
  display: grid;
  grid-template-columns: repeat(24, 1fr);
  gap: 3px;
  padding: 12px;
  border-radius: 12px;
  background: rgba(0,0,0,0.35);
  border: 1px solid var(--line);
  min-height: 140px;
}}
.photon-cell {{
  aspect-ratio: 1;
  border-radius: 2px;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}}
.photon-cell:hover {{
  transform: scale(1.35);
  z-index: 2;
  box-shadow: 0 0 10px currentColor;
}}
.photon-cell.L-2 {{ background: #f04a9e; color: #f04a9e; opacity: 0.95; }}
.photon-cell.L-1 {{ background: #c45a8a; color: #c45a8a; opacity: 0.75; }}
.photon-cell.L0  {{ background: rgba(255,255,255,0.12); color: rgba(255,255,255,0.2); }}
.photon-cell.L1  {{ background: #8aab2e; color: #8aab2e; opacity: 0.8; }}
.photon-cell.L2  {{ background: #c8f23a; color: #c8f23a; opacity: 1;
  box-shadow: 0 0 6px rgba(200,242,58,0.35); }}
.photon-cell.delta {{
  outline: 1px solid rgba(224,192,120,0.85);
  outline-offset: 0;
}}
.photon-meta {{
  display: flex;
  flex-direction: column;
  gap: 10px;
}}
.photon-stat {{
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: rgba(0,0,0,0.22);
}}
.photon-stat .k {{
  display: block;
  font-size: 0.58rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted2);
  margin-bottom: 4px;
  font-weight: 600;
}}
.photon-stat .v {{
  font-family: var(--mono);
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--ink);
}}
.photon-stat .v.lime {{ color: var(--lime); }}
.photon-stat .v.mag {{ color: var(--magenta); }}
.photon-stat .v.gold {{ color: var(--gold); }}
.photon-legend {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  margin-top: 12px;
  font-size: 0.62rem;
  color: var(--muted);
  letter-spacing: 0.04em;
}}
.photon-legend span {{
  display: inline-flex;
  align-items: center;
  gap: 5px;
}}
.photon-legend i {{
  width: 10px; height: 10px;
  border-radius: 2px;
  display: inline-block;
}}
.photon-bar {{
  height: 6px;
  border-radius: 99px;
  background: rgba(255,255,255,0.06);
  overflow: hidden;
  margin-top: 6px;
}}
.photon-bar > b {{
  display: block;
  height: 100%;
  border-radius: 99px;
  background: linear-gradient(90deg, var(--magenta), var(--gold), var(--lime));
  width: 0%;
  transition: width 0.6s ease;
}}

/* ΓöÇΓöÇ footer ΓöÇΓöÇ */
.foot {{
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px 20px;
  margin-top: clamp(24px, 3vw, 32px);
  padding-top: 16px;
  border-top: 1px solid var(--line);
  font-size: 0.52rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted2);
}}
.foot .live {{
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--lime);
  font-weight: 600;
}}
.foot .live::before {{
  content: "";
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--lime);
  box-shadow: 0 0 8px var(--lime-glow);
  animation: blink 2s ease-in-out infinite;
}}
.foot .live.reconnecting {{ color: var(--gold); }}
.foot .live.reconnecting::before {{
  background: var(--gold);
  box-shadow: 0 0 8px var(--gold-glow);
}}
.foot .live.offline {{ color: var(--magenta); }}
.foot .live.offline::before {{
  background: var(--magenta);
  box-shadow: 0 0 8px var(--magenta-glow);
  animation: none;
}}
.clock #scanTime {{ font-variant-numeric: tabular-nums; }}
.clock .stream-tag {{
  font-size: 0.52rem;
  letter-spacing: 0.14em;
  color: var(--muted2);
}}
.clock .stream-tag.on {{ color: var(--lime); }}
@keyframes blink {{
  0%, 100% {{ opacity: 1; }}
  50% {{ opacity: 0.35; }}
}}
.inspire {{
  width: 100%;
  margin-top: 2px;
  font-size: 0.58rem;
  letter-spacing: 0.02em;
  text-transform: none;
  color: var(--muted2);
  line-height: 1.4;
}}

/* ΓöÇΓöÇ audit (settings drawer) ΓöÇΓöÇ */
.audit {{
  margin-top: 28px;
  border-top: 1px solid var(--line);
  padding-top: 18px;
}}
.audit summary {{
  cursor: pointer;
  list-style: none;
  font-size: 0.58rem;
  font-weight: 600;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--muted);
  padding: 8px 0;
  min-height: 40px;
  display: flex;
  align-items: center;
  gap: 8px;
  -webkit-tap-highlight-color: transparent;
}}
.audit summary::-webkit-details-marker {{ display: none; }}
.audit summary::after {{
  content: "+";
  margin-left: auto;
  font-size: 1rem;
  color: var(--muted2);
}}
.audit[open] summary::after {{ content: "ΓêÆ"; }}
.table-card {{
  margin-top: 10px;
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--line);
  border-radius: 14px;
  overflow: hidden;
}}
.table-toolbar {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid var(--line);
  background: rgba(0,0,0,0.2);
}}
select, input[type="number"], .btn {{
  font-size: 0.72rem;
  border: 1px solid var(--line2);
  background: rgba(0,0,0,0.4);
  color: var(--ink);
  border-radius: 8px;
  padding: 9px 11px;
  min-height: 40px;
  -webkit-appearance: none;
  appearance: none;
}}
select {{
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' fill='none'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%238a857a' stroke-width='1.2'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
  padding-right: 28px;
}}
select option {{ background: #15171c; }}
.btn {{
  background: var(--lime);
  color: #0a0b0e;
  border-color: var(--lime);
  font-weight: 700;
  letter-spacing: 0.04em;
  cursor: pointer;
}}
.btn:active {{ transform: scale(0.98); }}
.table-wrap {{
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}}
table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 0.74rem;
  min-width: 720px;
}}
th {{
  text-align: left;
  padding: 11px 12px;
  font-size: 0.55rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
  background: rgba(0,0,0,0.25);
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
tr:hover td {{ background: rgba(255,255,255,0.025); }}
td.score {{
  font-family: var(--mono);
  font-weight: 700;
  font-size: 0.95rem;
  color: var(--lime);
}}
td.sym {{ font-weight: 600; color: var(--ink); }}
.bars {{ display: inline-flex; gap: 2px; vertical-align: middle; }}
.bars i {{
  width: 6px; height: 10px;
  border-radius: 1px;
  background: rgba(255,255,255,0.1);
  display: inline-block;
}}
.bars i.on {{ background: var(--lime); box-shadow: 0 0 5px var(--lime-glow); }}
.pos {{ color: var(--lime); font-weight: 600; }}
.neg {{ color: var(--magenta); font-weight: 600; }}
.path-cell svg {{ width: 72px; height: 28px; }}
.pill {{
  display: inline-flex;
  align-items: center;
  font-size: 0.55rem;
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
.pill.long, .pill.LONG {{
  color: var(--lime);
  border-color: rgba(198,239,58,0.35);
  background: rgba(198,239,58,0.1);
}}
.pill.short, .pill.SHORT {{
  color: var(--magenta);
  border-color: rgba(232,67,154,0.35);
  background: rgba(232,67,154,0.1);
}}
.pill.ready {{
  color: var(--lime);
  border-color: rgba(198,239,58,0.35);
  background: rgba(198,239,58,0.1);
}}
.pill.filtered {{
  color: var(--muted);
  background: rgba(255,255,255,0.03);
}}
.empty {{
  padding: 20px;
  text-align: center;
  color: var(--muted);
  font-size: 0.82rem;
}}
.meta-chip {{
  display: none;
}}

/* ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
   MOBILE ΓÇö visual perfection
   ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ */
@media (max-width: 900px) {{
  .stage {{
    grid-template-columns: 1fr 1fr;
    grid-template-areas:
      "left left"
      "orb orb"
      "stats stats";
    min-height: 0;
    gap: 8px 16px;
  }}
  .col-left {{ grid-area: left; padding-top: 0; }}
  .col-orb {{ grid-area: orb; padding: 12px 0 28px; }}
  .col-stats {{
    grid-area: stats;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    text-align: left;
    gap: 14px 12px;
    padding: 14px 0 4px;
    border-top: 1px solid var(--line);
  }}
  .nav {{
    flex-direction: row;
    flex-wrap: wrap;
    gap: 6px 16px;
    margin-top: 20px;
  }}
  .lower {{
    grid-template-columns: 1fr;
  }}
  .zen {{
    position: relative;
    width: 100%;
    max-width: 240px;
    height: 110px;
    margin: 18px 0 0 auto;
  }}
  .board-track {{
    mask-image: none;
    -webkit-mask-image: none;
  }}
}}

@media (max-width: 560px) {{
  .shell {{
    padding-left: calc(14px + var(--safe-l));
    padding-right: calc(14px + var(--safe-r));
  }}
  .topline {{ margin-bottom: 14px; }}
  .brand {{ letter-spacing: 0.2em; font-size: 0.58rem; }}
  .clock {{ font-size: 0.52rem; letter-spacing: 0.08em; gap: 8px; }}
  .wave {{ width: 28px; }}
  .eyebrow {{ margin-bottom: 14px; font-size: 0.55rem; max-width: none; }}
  .wordmark {{ font-size: clamp(2.4rem, 12vw, 3rem); letter-spacing: 0.06em; }}
  .tagline {{ max-width: none; }}
  .nav {{
    margin-top: 16px;
    gap: 4px 4px;
  }}
  .nav a {{
    font-size: 0.58rem;
    letter-spacing: 0.14em;
    padding: 6px 10px;
    border-radius: 999px;
    background: rgba(255,255,255,0.04);
    border: 1px solid var(--line);
    min-height: 34px;
  }}
  .nav a.on {{
    background: rgba(198,239,58,0.1);
    border-color: rgba(198,239,58,0.28);
  }}
  .blob {{
    --s: min(300px, 86vw);
  }}
  .blob-core {{ width: 82%; padding: 16px 12px; }}
  .blob-sym {{ letter-spacing: 0.1em; }}
  .col-stats {{
    grid-template-columns: repeat(2, 1fr);
    gap: 16px 14px;
  }}
  .stat .v {{ font-size: 1.15rem; }}
  .teardown {{
    grid-template-columns: 1fr;
    justify-items: center;
    text-align: center;
  }}
  .td-head {{ justify-content: center; }}
  .td-rows .row {{ text-align: left; }}
  .radar {{ max-width: 160px; margin: 0 auto; }}
  .overall {{ text-align: center; }}
  .proj-chart {{ height: 130px; }}
  .token {{ width: 84px; }}
  .sphere {{ width: 78px; height: 78px; }}
  .sphere .sym {{ font-size: 0.65rem; max-width: 66px; }}
  .sphere .sc {{ font-size: 1.05rem; }}
  .foot {{
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }}
  .table-toolbar {{
    flex-direction: column;
  }}
  select, input[type="number"], .btn {{
    width: 100%;
  }}
}}

@media (max-width: 380px) {{
  .col-stats {{ grid-template-columns: 1fr 1fr; }}
  .clock span {{ max-width: 42vw; overflow: hidden; text-overflow: ellipsis; }}
}}

@media (prefers-reduced-motion: reduce) {{
  .blob, .blob-shape, .blob-glass, .blob-ribbon, .foot .live::before {{
    animation: none !important;
  }}
}}
</style>
</head>
<body>
<div class="shell">
  <!-- TOP -->
  <header class="topline">
    <div class="brand">
      <div class="brand-mark" aria-hidden="true"><span></span><span></span><span></span></div>
      Acid Bourse
    </div>
    <div class="clock">
      <span id="scanTime">{gen_display}</span>
      <span class="stream-tag" id="streamTag">SCAN</span>
      <svg class="wave" viewBox="0 0 48 14" fill="none" aria-hidden="true">
        <path d="M0 7 Q3 1 6 7 T12 7 T18 7 T24 7 T30 7 T36 7 T42 7 T48 7" stroke="rgba(200,242,58,0.6)" stroke-width="1.2"/>
      </svg>
    </div>
  </header>

  <!-- HERO -->
  <section class="stage" id="overview">
    <div class="col-left">
      <p class="eyebrow">Intelligence layer<br/>for retail degenerates<br/>and market idiots.</p>
      <h1 class="wordmark">Idiot<br/><b>Flow</b></h1>
      <p class="tagline">The market's too complex.<br/>Follow the flow.</p>
      <nav>
        <ul class="nav">
          <li><a class="on" href="#overview">Overview</a></li>
          <li><a href="#signals">Signals</a></li>
          <li><a href="#board">Board</a></li>
          <li><a href="#photon">Photon</a></li>
          <li><a href="#teardown">Teardown</a></li>
          <li><a href="#settings">Settings</a></li>
        </ul>
      </nav>
    </div>

    <div class="col-orb">
      <div class="blob" id="heroBlob">
        <div class="blob-ribbon" aria-hidden="true"></div>
        <div class="blob-shape"></div>
        <div class="blob-glass"></div>
        <div class="blob-shine"></div>
        <div class="blob-shine2"></div>
        <div class="blob-core" id="heroSignal">
          <div class="blob-lbl">Primary signal</div>
          <div class="empty" style="padding:8px;font-size:0.8rem">No signals this scan.</div>
        </div>
      </div>
      <span class="drop d1" aria-hidden="true"></span>
      <span class="drop d2" aria-hidden="true"></span>
      <span class="drop d3" aria-hidden="true"></span>
      <div class="pool" aria-hidden="true"><i></i><i></i><i></i></div>
      <div class="pool-glow" aria-hidden="true"></div>
    </div>

    <aside class="col-stats" aria-label="Market stats">
      <div class="stat">
        <span class="k">Total flow 24h</span>
        <span class="v pos">{total_s}</span>
      </div>
      <div class="stat">
        <span class="k">Long flow 24h</span>
        <span class="v pos">{long_s}</span>
      </div>
      <div class="stat">
        <span class="k">Short flow 24h</span>
        <span class="v neg">{short_s}</span>
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
        <span class="k">Altcoin index</span>
        <span class="v">{alt_idx}</span>
        <span class="s dim">{alt_label}</span>
      </div>
    </aside>
  </section>

  <!-- FLOW PROJECTION -->
  <section class="projection" id="signals">
    <div class="proj-head">
      <h2>Flow projection</h2>
      <span class="sub">(based on flow)</span>
      <span class="info" title="Board path if price is flat">i</span>
    </div>
    <div class="proj-chart" id="pathChart"></div>
    <div class="proj-foot">
      <span>Entry zone ┬╖ <b id="pathTarget">ΓÇö</b></span>
      <span>Invalidation ┬╖ board cliff</span>
      <span>Time horizon: 0ΓÇô{horizon}h</span>
    </div>
  </section>

  <!-- THE BOARD -->
  <section class="board" id="board">
    <div class="board-head">
      <h2>The Board</h2>
      <span class="sub">Top opportunities</span>
      <span class="info" title="Ranked by strength">i</span>
    </div>
    <div class="board-track" id="ranked" role="list"></div>
  </section>

  <!-- PHOTON FSQ FINGERPRINT -->
  <section class="photon" id="photon" aria-label="Photon board fingerprint">
    <div class="photon-head">
      <div>
        <h2>Photon <em>FSQ</em> fingerprint</h2>
        <p class="sub">
          Board state quantized to Photon-style levels
          <b style="color:var(--ink2);font-weight:600">{{ΓêÆ1, ΓêÆ┬╜, 0, +┬╜, +1}}</b>
          ΓÇö discrete tokens from flow metrics, not raw pixels.
          Gold outline = changed vs last scan in this browser.
        </p>
      </div>
    </div>
    <div class="photon-grid-wrap">
      <div class="photon-lattice" id="photonLattice" aria-hidden="true"></div>
      <div class="photon-meta">
        <div class="photon-stat">
          <span class="k">Token grid</span>
          <span class="v lime" id="phTokens">ΓÇö</span>
        </div>
        <div class="photon-stat">
          <span class="k">╬ö vs last scan</span>
          <span class="v gold" id="phDelta">ΓÇö</span>
          <div class="photon-bar"><b id="phDeltaBar"></b></div>
        </div>
        <div class="photon-stat">
          <span class="k">Long / short mass</span>
          <span class="v" id="phSideMass">ΓÇö</span>
        </div>
        <div class="photon-stat">
          <span class="k">Entropy ┬╖ compression feel</span>
          <span class="v mag" id="phEntropy">ΓÇö</span>
        </div>
        <div class="photon-stat">
          <span class="k">Fingerprint hash</span>
          <span class="v" id="phHash" style="font-size:0.72rem;word-break:break-all">ΓÇö</span>
        </div>
      </div>
    </div>
    <div class="photon-legend">
      <span><i style="background:#f04a9e"></i> ΓêÆ1 strong short bias</span>
      <span><i style="background:#c45a8a"></i> ΓêÆ┬╜ soft short</span>
      <span><i style="background:rgba(255,255,255,0.2)"></i> 0 neutral</span>
      <span><i style="background:#8aab2e"></i> +┬╜ soft long</span>
      <span><i style="background:#c8f23a"></i> +1 strong long</span>
      <span><i style="outline:1px solid #e0c078;background:transparent"></i> ╬ö changed cell</span>
    </div>
  </section>

  <!-- TEARDOWN + NOTES -->
  <section class="lower" id="teardown">
    <div>
      <h3 class="sec-lbl">Signal teardown</h3>
      <div class="teardown">
        <div class="radar" id="radar"></div>
        <div>
          <div class="td-head">
            <span class="sym" id="tdSym">ΓÇö</span>
            <span class="side LONG" id="tdSide">ΓÇö</span>
          </div>
          <div class="td-rows" id="tdList"></div>
          <div class="overall">Overall conviction <b id="tdConv">ΓÇö</b></div>
        </div>
      </div>
    </div>
    <div class="notes-block">
      <h3 class="sec-lbl">Notes to self</h3>
      <ul class="notes-list">
        <li>Don't marry a coin.</li>
        <li>Invalidation is survival.</li>
        <li>Let winners run.</li>
        <li>Size small. Sleep well.</li>
        <li>Trade safe. Stay liquid.</li>
      </ul>
      <div class="zen" aria-hidden="true">
        <div class="zen-sand"></div>
        <div class="zen-ring"></div>
        <div class="zen-stone"></div>
        <svg class="zen-tree" viewBox="0 0 52 64" fill="none">
          <path d="M28 62 V36" stroke="#3d3c34" stroke-width="1.6" stroke-linecap="round"/>
          <path d="M28 48 Q18 42 14 48" stroke="#3d3c34" stroke-width="1.2" fill="none"/>
          <ellipse cx="26" cy="22" rx="16" ry="18" fill="#3a4230" opacity="0.85"/>
          <ellipse cx="20" cy="18" rx="9" ry="10" fill="#4a5340" opacity="0.55"/>
          <ellipse cx="32" cy="20" rx="8" ry="11" fill="#2e3528" opacity="0.5"/>
        </svg>
      </div>
    </div>
  </section>

  <!-- FOOTER -->
  <footer class="foot">
    <div>
      <span>Acid Bourse Systems</span>
      &nbsp;┬╖&nbsp;
      <span>Ver 2.1.0</span>
    </div>
    <div class="live offline" id="streamStatus">Data stream: connecting</div>
    <div id="uptimeLabel">Uptime ┬╖ {uptime}</div>
    <div class="inspire">
      Inspired by
      <a href="https://robotjames.substack.com/p/a-truly-idiotic-crypto-trade" target="_blank" rel="noopener">Robot James ΓÇö A truly idiotic crypto trade</a>
      ┬╖ independent tool, not affiliated ┬╖ {venue} ┬╖ {mode} ┬╖ {n_ideas} ideas ┬╖ {n_ad} adaptive ┬╖ {n_raw} raw
      ┬╖ Regime: {herd_bias}. {herd_note}
      Not financial advice.
    </div>
  </footer>

  <!-- SETTINGS / AUDIT -->
  <details class="audit" id="settings">
    <summary>Settings ┬╖ Full-board audit</summary>
    <div class="table-card">
      <div class="table-toolbar">
        <select id="sideFilter" aria-label="Side filter">
          <option value="ALL">All sides</option>
          <option value="LONG">Longs</option>
          <option value="SHORT">Shorts</option>
        </select>
        <select id="stateFilter" aria-label="State filter">
          <option value="ALL">All states</option>
          <option value="READY" selected>Ready only</option>
          <option value="FILTERED">Filtered out</option>
          <option value="PATH">Path / other</option>
        </select>
        <select id="sortBy" aria-label="Sort">
          <option value="score">Sort: score</option>
          <option value="strength">Sort: strength</option>
          <option value="delta">Sort: |╬ö|</option>
          <option value="outz">Sort: z-out</option>
          <option value="att">Sort: attention</option>
          <option value="vol">Sort: volume</option>
        </select>
        <input id="minStr" type="number" value="0" step="1" placeholder="Min strength" inputmode="decimal"/>
        <input id="minVol" type="number" value="0" step="10000" placeholder="Min vol" inputmode="decimal"/>
        <button class="btn" id="apply" type="button">Apply</button>
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
              <th>╬ö (1h)</th>
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
  </details>
</div>

<script id="payload" type="application/json">{data_json}</script>
<script>
const DATA = JSON.parse(document.getElementById('payload').textContent);
let selected = 0;
const LIVE = {{
  prices: {{}},
  status: 'connecting',
  ws: null,
  lastTick: 0,
  bootAt: Date.now(),
  reconnectMs: 1200,
}};

function fmt(n, d=2) {{
  if (n === undefined || n === null || Number.isNaN(+n)) return 'ΓÇö';
  return Number(n).toFixed(d);
}}
function fmtVol(v) {{
  if (v == null) return 'ΓÇö';
  const av = Math.abs(v);
  const sign = v < 0 ? '-' : (v > 0 ? '+' : '');
  if (av >= 1e9) return sign + '$' + (av/1e9).toFixed(2) + 'B';
  if (av >= 1e6) return sign + '$' + (av/1e6).toFixed(2) + 'M';
  if (av >= 1e3) return sign + '$' + (av/1e3).toFixed(1) + 'K';
  return sign + '$' + Math.round(av);
}}
function cls(n) {{ return n >= 0 ? 'pos' : 'neg'; }}
function baseSym(s) {{
  return (s || '').replace('-USDT-SWAP','').replace(/USDT$/,'');
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
function wordHi(v, hi, mid) {{
  if (v >= hi) return 'STRONG';
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

function sparkStep(path, w, h, color) {{
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
  for (let i = 1; i < coords.length; i++) d += ` L${{coords[i][0]}},${{coords[i][1]}}`;
  return `<svg viewBox="0 0 ${{w}} ${{h}}" preserveAspectRatio="none"><path d="${{d}}" fill="none" stroke="${{color}}" stroke-width="1.8" stroke-linejoin="round"/></svg>`;
}}

function bigPath(path, side) {{
  const pts = pathPoints(path);
  // responsive viewBox; CSS sizes the svg
  const w = 1000, h = 150, padL = 28, padR = 36, padT = 30, padB = 28;
  if (!pts) return '<div class="empty">No path</div>';
  const n = pts.path.length;
  const isLong = side !== 'SHORT';
  const stroke = isLong ? '#c8f23a' : '#f04a9e';
  const coords = pts.path.map((p, i) => {{
    const x = padL + (i / (n - 1)) * (w - padL - padR);
    const y = padT + (1 - (p.displayed_24h_pct - pts.min) / pts.span) * (h - padT - padB);
    return [x, y, p];
  }});
  // smooth curve
  let d = `M${{coords[0][0].toFixed(1)}},${{coords[0][1].toFixed(1)}}`;
  for (let i = 1; i < coords.length; i++) {{
    const mx = (coords[i-1][0] + coords[i][0]) / 2;
    d += ` C${{mx.toFixed(1)}},${{coords[i-1][1].toFixed(1)}} ${{mx.toFixed(1)}},${{coords[i][1].toFixed(1)}} ${{coords[i][0].toFixed(1)}},${{coords[i][1].toFixed(1)}}`;
  }}
  // dotted base path with markers T1..T4
  const marksAt = [0, Math.round((n-1)/3), Math.round(2*(n-1)/3), n-1];
  const marks = marksAt.map((i, mi) => {{
    const [x, y, p] = coords[i];
    const lab = 'T' + (mi + 1);
    // show price-ish or pct
    let val;
    if (p.ref_price != null && p.ref_price < 1) val = '$' + Number(p.ref_price).toFixed(6);
    else if (p.ref_price != null) val = '$' + Number(p.ref_price).toFixed(4);
    else val = p.displayed_24h_pct.toFixed(2) + '%';
    const anchor = mi === 0 ? 'start' : (mi === 3 ? 'end' : 'middle');
    return `
      <circle cx="${{x}}" cy="${{y}}" r="4.5" fill="${{stroke}}" stroke="#0a0b0e" stroke-width="1.5"/>
      <text x="${{x}}" y="${{y - 12}}" text-anchor="${{anchor}}" fill="${{stroke}}" font-size="10" font-family="Inter,sans-serif" font-weight="600" letter-spacing="0.12em">${{lab}}</text>
      <text x="${{x}}" y="${{h - 8}}" text-anchor="${{anchor}}" fill="rgba(200,196,186,0.5)" font-size="9" font-family="IBM Plex Mono,monospace">${{val}}</text>`;
  }}).join('');
  // entry zone label
  const entry = `
    <text x="${{coords[0][0]}}" y="${{coords[0][1] + 18}}" text-anchor="start" fill="rgba(138,133,122,0.8)" font-size="8" font-family="Inter,sans-serif" letter-spacing="0.12em">ENTRY ZONE</text>`;
  // invalidation dashed
  const invY = h - padB;
  return `<svg viewBox="0 0 ${{w}} ${{h}}" preserveAspectRatio="xMidYMid meet">
    <defs>
      <linearGradient id="ag" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="${{stroke}}" stop-opacity="0.22"/>
        <stop offset="100%" stop-color="${{stroke}}" stop-opacity="0"/>
      </linearGradient>
      <filter id="gl"><feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    </defs>
    <line x1="${{padL}}" y1="${{invY}}" x2="${{w - padR}}" y2="${{invY}}" stroke="rgba(232,67,154,0.35)" stroke-dasharray="5,5" stroke-width="1"/>
    <path d="${{d}} L${{coords.at(-1)[0]}},${{invY}} L${{coords[0][0]}},${{invY}} Z" fill="url(#ag)"/>
    <path d="${{d}}" fill="none" stroke="${{stroke}}" stroke-width="2" stroke-linejoin="round" filter="url(#gl)"/>
    ${{coords.filter((_,i)=>i%2===0).map(([x,y]) => `<circle cx="${{x}}" cy="${{y}}" r="1.6" fill="${{stroke}}" opacity="0.7"/>`).join('')}}
    ${{marks}}
    ${{entry}}
  </svg>`;
}}

function radarSvg(i) {{
  const str = Math.max(0, Math.min(100, i.strength_pine || i.score || 0));
  const liq = Math.max(0, Math.min(100, (i.liquidity_score || 0) * 2.5 || 45));
  const sent = Math.max(0, Math.min(100, i.attention_rank || 40));
  const edge = Math.max(0, Math.min(100, (Math.abs(i.roll_edge_z || 0) / 3) * 100));
  const rvol = Math.max(0, Math.min(100, Math.min(2.5, i.rvol || 0) / 2.5 * 100));
  const vals = [str, liq, sent, edge, rvol];
  // labels match mock: MOMENTUM, LIQUIDITY, SENTIMENT, STRUCTURE, VOL.ACCUM
  const labels = [
    {{ t: 'MOMENTUM', s: wordHi(str, 70, 45) }},
    {{ t: 'LIQUIDITY', s: wordHi(liq, 70, 45) }},
    {{ t: 'SENTIMENT', s: wordHi(sent, 70, 45) }},
    {{ t: 'STRUCTURE', s: wordHi(edge, 70, 45) }},
    {{ t: 'VOL. ACCUM.', s: wordHi(rvol, 70, 45) }},
  ];
  const cx = 70, cy = 72, R = 46;
  const n = 5;
  const pt = (v, k) => {{
    const a = -Math.PI / 2 + (k * 2 * Math.PI) / n;
    const r = (v / 100) * R;
    return [cx + r * Math.cos(a), cy + r * Math.sin(a)];
  }};
  const grid = [0.35, 0.7, 1].map(s => {{
    const pts = Array.from({{length: n}}, (_, k) => {{
      const a = -Math.PI / 2 + (k * 2 * Math.PI) / n;
      return `${{(cx + R * s * Math.cos(a)).toFixed(1)}},${{(cy + R * s * Math.sin(a)).toFixed(1)}}`;
    }}).join(' ');
    return `<polygon points="${{pts}}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="1"/>`;
  }}).join('');
  const axes = Array.from({{length: n}}, (_, k) => {{
    const a = -Math.PI / 2 + (k * 2 * Math.PI) / n;
    const x = cx + R * Math.cos(a), y = cy + R * Math.sin(a);
    const lx = cx + (R + 16) * Math.cos(a), ly = cy + (R + 16) * Math.sin(a);
    return `<line x1="${{cx}}" y1="${{cy}}" x2="${{x}}" y2="${{y}}" stroke="rgba(255,255,255,0.07)"/>
      <text x="${{lx.toFixed(1)}}" y="${{(ly - 5).toFixed(1)}}" text-anchor="middle" fill="rgba(138,133,122,0.95)" font-size="6.5" font-family="Inter,sans-serif" font-weight="600" letter-spacing="0.06em">${{labels[k].t}}</text>
      <text x="${{lx.toFixed(1)}}" y="${{(ly + 6).toFixed(1)}}" text-anchor="middle" fill="#c8f23a" font-size="6.5" font-family="Inter,sans-serif" font-weight="700" letter-spacing="0.04em">${{labels[k].s}}</text>`;
  }}).join('');
  const poly = vals.map((v, k) => pt(v, k).map(x => x.toFixed(1)).join(',')).join(' ');
  const dots = vals.map((v, k) => {{
    const [x, y] = pt(v, k);
    return `<circle cx="${{x.toFixed(1)}}" cy="${{y.toFixed(1)}}" r="2.4" fill="#c8f23a"/>`;
  }}).join('');
  return `<svg viewBox="0 0 140 144">
    ${{grid}}${{axes}}
    <polygon points="${{poly}}" fill="rgba(200,242,58,0.16)" stroke="#c8f23a" stroke-width="1.6"/>
    ${{dots}}
  </svg>`;
}}

function listForRank() {{
  const pot = DATA.potato || [];
  if (pot.length) return pot;
  return (DATA.ideas || []).slice(0, 8);
}}

function fmtPrice(p) {{
  if (p == null || Number.isNaN(+p)) return 'ΓÇö';
  const n = Number(p);
  if (n >= 1000) return n.toLocaleString(undefined, {{ maximumFractionDigits: 2 }});
  if (n >= 1) return n.toFixed(4);
  if (n >= 0.01) return n.toFixed(6);
  return n.toPrecision(4);
}}

function liveFor(sym) {{
  return LIVE.prices[sym] || null;
}}

function renderHero(i) {{
  const el = document.getElementById('heroSignal');
  if (!i) {{
    el.innerHTML = '<div class="blob-lbl">Primary signal</div><div class="empty" style="padding:8px;font-size:0.8rem">No signals this scan.</div>';
    document.getElementById('pathChart').innerHTML = '<div class="empty">No path</div>';
    document.getElementById('pathTarget').textContent = 'ΓÇö';
    renderTeardown(null);
    return;
  }}
  const str = i.strength_pine || i.score || 0;
  const side = i.side || 'ΓÇö';
  const conv = conviction(str);
  const arrow = side === 'SHORT' ? 'Γåô' : 'Γåæ';
  const L = liveFor(i.symbol);
  const px = L ? L.price : i.price;
  const chg = L && L.chgPct != null ? L.chgPct : i.current_24h_pct;
  const chgCls = chg == null ? '' : (chg >= 0 ? 'up' : 'dn');
  const chgStr = chg == null ? '' : ((chg >= 0 ? '+' : '') + fmt(chg) + '%');
  el.innerHTML = `
    <div class="blob-lbl">Primary signal</div>
    <h2 class="blob-sym">${{baseSym(i.symbol)}}<span class="blob-pair">/USDT</span></h2>
    <div class="blob-live" id="heroLive"><span class="px">${{fmtPrice(px)}}</span>${{chgStr ? `<span class="chg ${{chgCls}}">${{chgStr}}</span>` : ''}}</div>
    <div class="blob-side ${{side}}">${{side}} <span class="arr">${{arrow}}</span></div>
    <div class="blob-score-lbl">Flow score</div>
    <div class="blob-score">${{Math.round(str)}}</div>
    <div class="blob-conv ${{conv.cls}}">Conviction: <b>${{conv.label}}</b></div>
  `;
  document.getElementById('pathChart').innerHTML = bigPath(i.path, side);
  // Live-adjusted board path: reprice current 24h from live last vs scan ref
  const pathHint = livePathHint(i);
  document.getElementById('pathTarget').textContent = pathHint ||
    `${{fmt(i.current_24h_pct)}}% ΓåÆ ${{fmt(i.flat_next_24h_pct)}}%  (╬ö ${{fmt(i.known_roll_delta_pp)}}pp)`;
  renderTeardown(i);
}}

function livePathHint(i) {{
  const L = liveFor(i.symbol);
  if (!L || !i.path || !i.path.length) return null;
  const ref0 = i.path[0] && i.path[0].ref_price;
  if (!ref0) return `${{fmt(L.chgPct)}}% live ┬╖ ╬ö ${{fmt(i.known_roll_delta_pp)}}pp cliff`;
  const livePct = ((L.price / ref0) - 1) * 100;
  const next = livePct + (i.known_roll_delta_pp || 0);
  return `${{fmt(livePct)}}% ΓåÆ ${{fmt(next)}}%  (╬ö ${{fmt(i.known_roll_delta_pp)}}pp ┬╖ live)`;
}}

function renderTeardown(i) {{
  if (!i) {{
    document.getElementById('tdSym').textContent = 'ΓÇö';
    document.getElementById('tdSide').textContent = 'ΓÇö';
    document.getElementById('tdList').innerHTML = '';
    document.getElementById('tdConv').textContent = 'ΓÇö';
    document.getElementById('radar').innerHTML = '';
    return;
  }}
  const str = i.strength_pine || i.score || 0;
  const side = i.side || 'ΓÇö';
  document.getElementById('tdSym').textContent = baseSym(i.symbol) + ' /USDT';
  const sideEl = document.getElementById('tdSide');
  sideEl.textContent = side;
  sideEl.className = 'side ' + side;
  document.getElementById('tdConv').textContent = conviction(str).label;
  document.getElementById('radar').innerHTML = radarSvg(i);

  // Match mock metric language, driven by real fields
  const edgeZ = Math.abs(i.roll_edge_z || 0);
  const outZ = Math.abs(i.outgoing_z || 0);
  const att = i.attention_rank || 0;
  const rvol = i.rvol || 0;
  const trend = i.recent_trend_pct || 0;
  const rows = [
    ['Smart Money Flow', wordHi(str, 70, 50), str >= 50 ? 'hi' : ''],
    ['Exchange Net Flow', side === 'LONG' ? 'POSITIVE' : 'NEGATIVE', side === 'LONG' ? 'hi' : 'neg'],
    ['Whale Accumulation', att >= 70 ? 'HIGH' : (att >= 40 ? 'MED' : 'LOW'), att >= 70 ? 'hi' : ''],
    ['Price Structure', trend >= 0 ? 'BULLISH' : 'BEARISH', trend >= 0 ? 'hi' : 'neg'],
    ['Derivatives Bias', side === 'LONG' ? 'LONG' : 'SHORT', side === 'LONG' ? 'hi' : 'neg'],
    ['Social Sentiment', att >= 60 ? 'NEUTRAL+' : (att >= 30 ? 'NEUTRAL' : 'SOFT'), att >= 60 ? 'hi' : ''],
    ['Liquidity Heatmap', rvol >= 0.8 ? 'CLEAN' : (rvol >= 0.3 ? 'THIN' : 'DRY'), rvol >= 0.8 ? 'hi' : ''],
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
    // prefer dollar flow; fall back to delta pp
    let flow = fmtVol(i.roll_volume);
    if (i.known_roll_delta_pp != null && Math.abs(i.roll_volume || 0) < 1) {{
      flow = (i.known_roll_delta_pp >= 0 ? '+' : '') + fmt(i.known_roll_delta_pp) + 'pp';
    }}
    const arrow = side === 'SHORT' ? 'Γåô' : 'Γåæ';
    const L = liveFor(i.symbol);
    const px = L ? L.price : i.price;
    const chg = L && L.chgPct != null ? L.chgPct : i.current_24h_pct;
    const pxCls = chg == null ? '' : (chg >= 0 ? 'up' : 'dn');
    const chgStr = chg == null ? '' : ((chg >= 0 ? '+' : '') + fmt(chg, 2) + '%');
    return `
    <article class="token ${{side}} ${{idx === selected ? 'on' : ''}}" data-idx="${{idx}}" data-sym="${{i.symbol}}" role="listitem" tabindex="0">
      <div class="sphere">
        <span class="idx">${{String(idx + 1).padStart(2,'0')}}</span>
        <div>
          <div class="sym">${{baseSym(i.symbol)}}</div>
          <div class="sc">${{str}}</div>
        </div>
      </div>
      <div class="flow">${{flow}}</div>
      <div class="live-px ${{pxCls}}" data-live-px>${{fmtPrice(px)}}</div>
      <div class="live-chg ${{pxCls}}" data-live-chg>${{chgStr}}</div>
      <div class="mirror"></div>
      <div class="arrow">${{arrow}}</div>
    </article>`;
  }}).join('');

  const activate = (idx) => {{
    selected = idx;
    renderRanked();
    renderHero(list[selected]);
    // scroll selected into view on mobile
    const node = el.querySelector(`[data-idx="${{idx}}"]`);
    if (node) node.scrollIntoView({{ behavior: 'smooth', inline: 'center', block: 'nearest' }});
  }};
  el.querySelectorAll('.token').forEach(card => {{
    card.addEventListener('click', () => activate(+card.dataset.idx));
    card.addEventListener('keydown', (e) => {{
      if (e.key === 'Enter' || e.key === ' ') {{ e.preventDefault(); activate(+card.dataset.idx); }}
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
    tb.innerHTML = '<tr><td colspan="12" class="empty">No rows match these filters. Try ΓÇ£All statesΓÇ¥.</td></tr>';
    return;
  }}
  tb.innerHTML = rows.map(i => `
    <tr>
      <td class="score">${{Math.round(i.strength_pine || i.score || 0)}}</td>
      <td>${{strengthBars(i.strength_pine || 0)}}</td>
      <td>${{statePill(i.setup_state)}}</td>
      <td class="sym">${{i.symbol}}</td>
      <td><span class="pill ${{(i.side || '').toLowerCase()}}">${{i.side}}</span></td>
      <td class="${{cls(i.known_roll_delta_pp)}}">${{fmt(i.known_roll_delta_pp)}}%</td>
      <td>${{fmt(i.outgoing_z,2)}}</td>
      <td>${{fmt(i.roll_edge_z,2)}}</td>
      <td>${{fmt(i.attention_rank,0)}}p</td>
      <td>${{fmt(i.rvol,2)}}x</td>
      <td>${{fmtVol(i.roll_volume)}}</td>
      <td class="path-cell">${{sparkStep(i.path, 72, 28, i.side === 'SHORT' ? '#f04a9e' : '#c8f23a')}}</td>
    </tr>
  `).join('');
}}

// nav active state
document.querySelectorAll('.nav a').forEach(a => {{
  a.addEventListener('click', () => {{
    document.querySelectorAll('.nav a').forEach(x => x.classList.remove('on'));
    a.classList.add('on');
  }});
}});

document.getElementById('apply').onclick = renderTable;
['sideFilter','stateFilter','sortBy','minStr','minVol'].forEach(id => {{
  document.getElementById(id).addEventListener('change', renderTable);
}});

/* ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
   REAL-TIME ΓÇö Binance miniTicker WS + REST
   ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ */
function allSymbols() {{
  const s = new Set();
  (DATA.ideas || []).forEach(i => i.symbol && s.add(i.symbol));
  (DATA.potato || []).forEach(i => i.symbol && s.add(i.symbol));
  return [...s];
}}

function setStreamStatus(state, label) {{
  LIVE.status = state;
  const el = document.getElementById('streamStatus');
  const tag = document.getElementById('streamTag');
  if (el) {{
    el.className = 'live ' + state;
    el.textContent = label || ({{
      live: 'Data stream: live',
      reconnecting: 'Data stream: reconnecting',
      offline: 'Data stream: offline',
      connecting: 'Data stream: connecting',
    }}[state] || 'Data stream: ' + state);
  }}
  if (tag) {{
    tag.textContent = state === 'live' ? 'LIVE' : (state === 'reconnecting' ? 'SYNC' : 'SCAN');
    tag.classList.toggle('on', state === 'live');
  }}
}}

function applyTick(sym, price, chgPct) {{
  if (!sym || price == null) return;
  const prev = LIVE.prices[sym];
  const dir = prev && price > prev.price ? 'up' : (prev && price < prev.price ? 'dn' : null);
  LIVE.prices[sym] = {{
    price: +price,
    chgPct: chgPct != null ? +chgPct : (prev && prev.chgPct),
    t: Date.now(),
  }};
  LIVE.lastTick = Date.now();

  // Board tokens ΓÇö surgical DOM update (no full re-render)
  document.querySelectorAll(`.token[data-sym="${{sym}}"]`).forEach(card => {{
    const pxEl = card.querySelector('[data-live-px]');
    const chEl = card.querySelector('[data-live-chg]');
    const L = LIVE.prices[sym];
    if (pxEl) {{
      pxEl.textContent = fmtPrice(L.price);
      pxEl.className = 'live-px ' + (L.chgPct >= 0 ? 'up' : 'dn');
    }}
    if (chEl && L.chgPct != null) {{
      chEl.textContent = (L.chgPct >= 0 ? '+' : '') + fmt(L.chgPct) + '%';
      chEl.className = 'live-chg ' + (L.chgPct >= 0 ? 'up' : 'dn');
    }}
  }});

  // Hero ΓÇö only if selected
  const list = listForRank();
  const cur = list[selected];
  if (cur && cur.symbol === sym) {{
    const hero = document.getElementById('heroLive');
    if (hero) {{
      const chg = LIVE.prices[sym].chgPct;
      const chgCls = chg == null ? '' : (chg >= 0 ? 'up' : 'dn');
      const chgStr = chg == null ? '' : ((chg >= 0 ? '+' : '') + fmt(chg) + '%');
      hero.innerHTML = `<span class="px">${{fmtPrice(price)}}</span>${{chgStr ? `<span class="chg ${{chgCls}}">${{chgStr}}</span>` : ''}}`;
      if (dir) {{
        hero.classList.remove('flash-up', 'flash-dn');
        void hero.offsetWidth;
        hero.classList.add(dir === 'up' ? 'flash-up' : 'flash-dn');
        setTimeout(() => hero.classList.remove('flash-up', 'flash-dn'), 280);
      }}
      const pathHint = livePathHint(cur);
      if (pathHint) document.getElementById('pathTarget').textContent = pathHint;
    }}
  }}
}}

const WS_HOSTS = [
  'wss://data-stream.binance.vision/stream',
  'wss://stream.binance.com:9443/stream',
  'wss://stream.binance.com:443/stream',
];
const REST_HOSTS = [
  'https://data-api.binance.vision',
  'https://www.binance.com',
  'https://api.binance.us',
  'https://api.binance.com',
];
let wsHostIdx = 0;
let restHostIdx = 0;

function connectBinanceWS() {{
  const syms = allSymbols();
  if (!syms.length) {{
    setStreamStatus('offline', 'Data stream: no symbols');
    return;
  }}
  // Combined miniTicker stream (CORS-free WS from browser)
  const streams = syms.map(s => s.toLowerCase() + '@miniTicker').join('/');
  const base = WS_HOSTS[wsHostIdx % WS_HOSTS.length];
  const url = base + '?streams=' + streams;
  setStreamStatus('connecting');
  try {{
    if (LIVE.ws) {{
      try {{ LIVE.ws.close(); }} catch (_) {{}}
    }}
    const ws = new WebSocket(url);
    LIVE.ws = ws;
    let opened = false;
    ws.onopen = () => {{
      opened = true;
      LIVE.reconnectMs = 1200;
      setStreamStatus('live');
    }};
    ws.onmessage = (ev) => {{
      try {{
        const msg = JSON.parse(ev.data);
        const d = msg.data || msg;
        // miniTicker: s=symbol, c=close, o=open, P=priceChangePercent
        const sym = d.s;
        const price = d.c != null ? +d.c : null;
        const chg = d.P != null ? +d.P : (d.o && d.c ? ((+d.c / +d.o) - 1) * 100 : null);
        if (sym && price != null) applyTick(sym, price, chg);
      }} catch (_) {{}}
    }};
    ws.onerror = () => {{
      setStreamStatus('reconnecting');
    }};
    ws.onclose = () => {{
      if (!opened) wsHostIdx = (wsHostIdx + 1) % WS_HOSTS.length;
      setStreamStatus('reconnecting');
      const wait = Math.min(20000, LIVE.reconnectMs);
      LIVE.reconnectMs = Math.min(20000, LIVE.reconnectMs * 1.55);
      setTimeout(connectBinanceWS, wait);
    }};
  }} catch (e) {{
    wsHostIdx = (wsHostIdx + 1) % WS_HOSTS.length;
    setStreamStatus('offline');
    setTimeout(connectBinanceWS, 5000);
  }}
}}

async function fetchTickerBatch(host, syms) {{
  // Prefer all-tickers then filter (one request)
  const res = await fetch(host + '/api/v3/ticker/24hr', {{ cache: 'no-store' }});
  if (!res.ok) throw new Error('batch ' + res.status);
  const rows = await res.json();
  const want = new Set(syms);
  let n = 0;
  for (const r of rows) {{
    if (!want.has(r.symbol)) continue;
    applyTick(r.symbol, +r.lastPrice, +r.priceChangePercent);
    n++;
  }}
  return n;
}}

async function fetchTickerEach(host, syms) {{
  let n = 0;
  await Promise.all(syms.slice(0, 16).map(async sym => {{
    try {{
      const r = await fetch(host + '/api/v3/ticker/24hr?symbol=' + encodeURIComponent(sym), {{ cache: 'no-store' }});
      if (!r.ok) return;
      const d = await r.json();
      applyTick(sym, +d.lastPrice, +d.priceChangePercent);
      n++;
    }} catch (_) {{}}
  }}));
  return n;
}}

async function refreshRestTickers() {{
  const syms = allSymbols();
  if (!syms.length) return;
  // Rotate through public REST hosts (geo / 451 resilience)
  const order = [...Array(REST_HOSTS.length)].map((_, i) => REST_HOSTS[(restHostIdx + i) % REST_HOSTS.length]);
  for (const host of order) {{
    try {{
      let n = 0;
      try {{
        n = await fetchTickerBatch(host, syms);
      }} catch (_) {{
        n = await fetchTickerEach(host, syms);
      }}
      if (n > 0) {{
        restHostIdx = REST_HOSTS.indexOf(host);
        if (LIVE.status !== 'live') setStreamStatus('live', 'Data stream: live (rest)');
        return;
      }}
    }} catch (_) {{}}
  }}
}}

function tickClock() {{
  const el = document.getElementById('scanTime');
  if (!el) return;
  const d = new Date();
  const pad = n => String(n).padStart(2, '0');
  // Local wall clock (browser TZ) ΓÇö feels live
  el.textContent =
    d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + ' ' +
    pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
  // Session uptime
  const up = document.getElementById('uptimeLabel');
  if (up) {{
    const secs = Math.floor((Date.now() - LIVE.bootAt) / 1000);
    const m = Math.floor(secs / 60), s = secs % 60;
    const h = Math.floor(m / 60);
    const body = h > 0
      ? (h + 'H ' + String(m % 60).padStart(2, '0') + 'M ' + String(s).padStart(2, '0') + 'S')
      : (m + 'M ' + String(s).padStart(2, '0') + 'S');
    const stale = LIVE.lastTick && (Date.now() - LIVE.lastTick > 15000);
    up.textContent = 'Uptime ┬╖ ' + body + (stale && LIVE.status === 'live' ? ' ┬╖ stale' : '');
  }}
}}

/* ΓöÇΓöÇ Photon-FSQ style fingerprint (numeric board ΓåÆ discrete tokens) ΓöÇΓöÇ */
const FSQ_LEVELS = [-1, -0.5, 0, 0.5, 1];
const PHOTON_KEY = 'ifb_photon_fp_v1';

function quantizeFSQ(x) {{
  // map continuous score in [-1,1] to nearest Photon level
  let best = 0, bestD = Infinity;
  for (let i = 0; i < FSQ_LEVELS.length; i++) {{
    const d = Math.abs(x - FSQ_LEVELS[i]);
    if (d < bestD) {{ bestD = d; best = i; }}
  }}
  return best; // 0..4
}}

function clamp01(x) {{ return Math.max(0, Math.min(1, x)); }}

function ideaToToken(i) {{
  // Side-signed strength + edge shock ΓåÆ one discrete level
  const str = (+i.strength_pine || +i.score || 0) / 100;
  const edge = Math.min(1, Math.abs(+i.outgoing_z || 0) / 4);
  const att = clamp01((+i.attention_rank || 50) / 100);
  const rvol = Math.min(1, (+i.rvol || 0) / 2);
  const signed = (i.side === 'LONG' ? 1 : -1) * (0.55 * str + 0.25 * edge + 0.12 * att + 0.08 * rvol);
  // squash to [-1,1]
  const x = Math.tanh(signed * 1.4);
  return quantizeFSQ(x);
}}

function buildPhotonGrid() {{
  const ideas = (DATA.ideas || []).slice().sort((a, b) =>
    Math.abs(b.strength_pine || b.score || 0) - Math.abs(a.strength_pine || a.score || 0)
  );
  const cols = 24;
  const rows = 8;
  const n = cols * rows;
  const tokens = new Array(n).fill(2); // neutral L0
  // Place top ideas; fill rest with herd-biased noise from meta
  const herd = (DATA.meta && DATA.meta.herd) || {{}};
  const longBias = (+herd.long_share || 0.5) - 0.5; // -0.5..0.5
  for (let k = 0; k < n; k++) {{
    if (k < ideas.length) {{
      tokens[k] = ideaToToken(ideas[k]);
    }} else {{
      // ambient lattice from regime + position
      const t = (k / n) * 2 - 1;
      const amb = Math.tanh(longBias * 1.6 + t * 0.15);
      tokens[k] = quantizeFSQ(amb + ((k * 17) % 5 - 2) * 0.08);
    }}
  }}
  return {{ tokens, cols, rows, n, ideas: ideas.slice(0, Math.min(ideas.length, n)) }};
}}

function levelClass(idx) {{
  return ['L-2', 'L-1', 'L0', 'L1', 'L2'][idx] || 'L0';
}}

function simpleHash(arr) {{
  let h = 2166136261;
  for (let i = 0; i < arr.length; i++) {{
    h ^= arr[i] + 1;
    h = Math.imul(h, 16777619);
  }}
  return ('00000000' + (h >>> 0).toString(16)).slice(-8);
}}

function entropyBits(tokens) {{
  const counts = [0, 0, 0, 0, 0];
  tokens.forEach(t => {{ counts[t] = (counts[t] || 0) + 1; }});
  const n = tokens.length || 1;
  let H = 0;
  counts.forEach(c => {{
    if (!c) return;
    const p = c / n;
    H -= p * Math.log2(p);
  }});
  return H;
}}

function renderPhoton() {{
  const lattice = document.getElementById('photonLattice');
  if (!lattice) return;
  const {{ tokens, n, ideas }} = buildPhotonGrid();
  let prev = null;
  try {{ prev = JSON.parse(localStorage.getItem(PHOTON_KEY) || 'null'); }} catch (_) {{}}

  let changed = 0;
  const prevTok = prev && Array.isArray(prev.tokens) ? prev.tokens : null;
  lattice.innerHTML = tokens.map((t, i) => {{
    const delta = prevTok && prevTok[i] !== t;
    if (delta) changed++;
    const tip = ideas[i]
      ? (ideas[i].symbol + ' ' + ideas[i].side + ' ┬╖ L' + FSQ_LEVELS[t])
      : ('ambient ┬╖ L' + FSQ_LEVELS[t]);
    return `<div class="photon-cell ${{levelClass(t)}}${{delta ? ' delta' : ''}}" title="${{tip}}"></div>`;
  }}).join('');

  const deltaPct = prevTok ? Math.round(100 * changed / n) : 0;
  const H = entropyBits(tokens);
  const maxH = Math.log2(5);
  const longN = tokens.filter(t => t >= 3).length;
  const shortN = tokens.filter(t => t <= 1).length;
  const hash = simpleHash(tokens);

  const el = id => document.getElementById(id);
  if (el('phTokens')) el('phTokens').textContent = n + ' ┬╖ 5 levels ┬╖ dim 1';
  if (el('phDelta')) {{
    el('phDelta').textContent = prevTok
      ? (changed + ' cells ┬╖ ' + deltaPct + '%')
      : 'first scan in this browser';
  }}
  if (el('phDeltaBar')) el('phDeltaBar').style.width = (prevTok ? deltaPct : 8) + '%';
  if (el('phSideMass')) {{
    el('phSideMass').innerHTML =
      '<span class="lime">' + longN + ' long</span> / <span class="mag">' + shortN + ' short</span>';
  }}
  if (el('phEntropy')) {{
    el('phEntropy').textContent =
      H.toFixed(2) + ' / ' + maxH.toFixed(2) + ' bits ┬╖ ' + Math.round(100 * (1 - H / maxH)) + '% ordered';
  }}
  if (el('phHash')) el('phHash').textContent = 'fsq_' + hash;

  try {{
    localStorage.setItem(PHOTON_KEY, JSON.stringify({{
      tokens,
      t: Date.now(),
      generated_at: (DATA.meta && DATA.meta.generated_at) || null,
      hash: 'fsq_' + hash,
    }}));
  }} catch (_) {{}}
}}

// Seed from scan snapshot so UI is never empty before first tick
(DATA.ideas || []).forEach(i => {{
  if (i.symbol && i.price != null) {{
    LIVE.prices[i.symbol] = {{ price: +i.price, chgPct: i.current_24h_pct, t: 0 }};
  }}
}});
(DATA.potato || []).forEach(i => {{
  if (i.symbol && i.price != null && !LIVE.prices[i.symbol]) {{
    LIVE.prices[i.symbol] = {{ price: +i.price, chgPct: i.current_24h_pct, t: 0 }};
  }}
}});

const rankList = listForRank();
renderHero(rankList[0]);
renderRanked();
const hasReady = (DATA.ideas || []).some(i => (i.setup_state || '').includes('READY'));
if (!hasReady) document.getElementById('stateFilter').value = 'ALL';
renderTable();
renderPhoton();

tickClock();
setInterval(tickClock, 1000);
connectBinanceWS();
refreshRestTickers();
setInterval(refreshRestTickers, 45000);

// Visibility: reconnect when tab returns
document.addEventListener('visibilitychange', () => {{
  if (document.visibilityState === 'visible') {{
    if (!LIVE.ws || LIVE.ws.readyState > 1) connectBinanceWS();
    refreshRestTickers();
  }}
}});
</script>
</body>
</html>
"""
    out_path = Path(out_path)
    out_path.write_text(html, encoding="utf-8")
    return out_path
