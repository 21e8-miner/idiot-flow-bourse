#!/usr/bin/env python3
"""Generate Idiot Flow Lab HTML — Acid Bourse visual system."""

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
    herd_bias = _esc(str(herd.get("bias", "n/a")))
    herd_note = _esc(str(herd.get("note", "")))
    generated = _esc(str(meta.get("generated_at", "")))
    venue = _esc(str(meta.get("venue", "")))
    mode = _esc(str(meta.get("mode", "adaptive")))
    n_ad = meta.get("n_adaptive", herd.get("n_adaptive", 0))
    n_raw = meta.get("n_classic_raw", 0)
    n_ideas = meta.get("n_ideas", len(ideas))

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Idiot Flow · Acid Bourse</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,600;12..96,800&family=IBM+Plex+Mono:wght@400;500;600&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400&display=swap" rel="stylesheet"/>
<style>
  :root {{
    --ink: #100e14;
    --ink2: #1a1622;
    --ink3: #241f2e;
    --cream: #f3ead7;
    --cream2: #e8dcc4;
    --fog: #a89bb8;
    --acid: #d6ff3c;
    --acid-dim: rgba(214, 255, 60, 0.12);
    --violet: #8b5cf6;
    --violet-dim: rgba(139, 92, 246, 0.15);
    --mint: #3ef0c2;          /* LONG — not traffic green */
    --mint-dim: rgba(62, 240, 194, 0.12);
    --hot: #ff4d9a;           /* SHORT — hot magenta, not red */
    --hot-dim: rgba(255, 77, 154, 0.12);
    --amber: #ffb020;
    --line: rgba(243, 234, 215, 0.12);
    --line2: rgba(243, 234, 215, 0.22);
    --display: "Bricolage Grotesque", system-ui, sans-serif;
    --serif: "Newsreader", Georgia, serif;
    --mono: "IBM Plex Mono", ui-monospace, monospace;
  }}

  * {{ box-sizing: border-box; }}
  html {{ scroll-behavior: smooth; }}
  body {{
    margin: 0;
    min-height: 100vh;
    color: var(--cream);
    font-family: var(--serif);
    background:
      radial-gradient(ellipse 90% 60% at 100% -10%, rgba(139, 92, 246, 0.22), transparent 55%),
      radial-gradient(ellipse 70% 50% at -10% 30%, rgba(214, 255, 60, 0.08), transparent 50%),
      radial-gradient(ellipse 50% 40% at 70% 100%, rgba(255, 77, 154, 0.08), transparent 50%),
      var(--ink);
    overflow-x: hidden;
  }}

  /* paper grain */
  body::before {{
    content: "";
    pointer-events: none;
    position: fixed;
    inset: 0;
    opacity: 0.04;
    z-index: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  }}

  .shell {{ position: relative; z-index: 1; max-width: 1280px; margin: 0 auto; padding: 0 22px 56px; }}

  /* ── masthead ── */
  .masthead {{
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 20px;
    padding: 36px 0 22px;
    border-bottom: 3px solid var(--cream);
    margin-bottom: 8px;
  }}
  .kicker {{
    font-family: var(--mono);
    font-size: 0.72rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--acid);
    margin: 0 0 10px;
  }}
  .masthead h1 {{
    font-family: var(--display);
    font-weight: 800;
    font-size: clamp(2.4rem, 6vw, 4.2rem);
    line-height: 0.92;
    letter-spacing: -0.04em;
    margin: 0;
    text-transform: uppercase;
  }}
  .masthead h1 em {{
    font-style: normal;
    color: var(--acid);
    display: inline-block;
    transform: rotate(-2deg);
  }}
  .deck {{
    margin: 14px 0 0;
    max-width: 36rem;
    font-size: 1.08rem;
    line-height: 1.45;
    color: var(--fog);
    font-weight: 400;
  }}
  .deck strong {{ color: var(--cream); font-weight: 600; }}

  .stamp {{
    align-self: start;
    border: 2px solid var(--acid);
    color: var(--acid);
    font-family: var(--mono);
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    padding: 14px 16px;
    transform: rotate(4deg);
    background: var(--acid-dim);
    text-align: center;
    line-height: 1.5;
    min-width: 120px;
  }}
  .stamp b {{
    display: block;
    font-family: var(--display);
    font-size: 1.6rem;
    letter-spacing: -0.03em;
    color: var(--cream);
    margin-top: 2px;
  }}

  /* ── ticker meta ── */
  .ticker {{
    display: flex;
    flex-wrap: wrap;
    gap: 0;
    border-bottom: 1px solid var(--line2);
    margin-bottom: 28px;
    font-family: var(--mono);
    font-size: 0.74rem;
  }}
  .tick {{
    padding: 12px 16px;
    border-right: 1px solid var(--line);
    color: var(--fog);
  }}
  .tick:last-child {{ border-right: none; }}
  .tick b {{ color: var(--cream); font-weight: 600; }}
  .tick.hi b {{ color: var(--acid); }}
  .tick.warn b {{ color: var(--amber); }}
  .tick.hot b {{ color: var(--hot); }}
  .tick.mint b {{ color: var(--mint); }}

  .lede {{
    font-family: var(--serif);
    font-style: italic;
    font-size: 1.05rem;
    color: var(--fog);
    margin: -8px 0 32px;
    padding-left: 14px;
    border-left: 3px solid var(--violet);
    max-width: 48rem;
    line-height: 1.5;
  }}

  /* ── sections ── */
  section {{ margin-bottom: 40px; }}
  .sec-head {{
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 16px;
  }}
  .sec-head h2 {{
    font-family: var(--display);
    font-weight: 800;
    font-size: 0.95rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin: 0;
    color: var(--cream);
  }}
  .sec-head h2 span {{
    color: var(--violet);
    font-weight: 600;
  }}
  .sec-note {{
    font-family: var(--mono);
    font-size: 0.68rem;
    color: var(--fog);
    letter-spacing: 0.06em;
  }}

  /* ── potato tickets ── */
  .potato-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 16px;
  }}
  .ticket {{
    position: relative;
    background:
      linear-gradient(145deg, var(--ink3) 0%, var(--ink2) 100%);
    border: 1px solid var(--line2);
    border-radius: 4px 18px 4px 18px;
    padding: 18px 18px 16px;
    overflow: hidden;
    transition: transform 0.18s ease, border-color 0.18s ease;
  }}
  .ticket:hover {{
    transform: translateY(-3px) rotate(-0.3deg);
    border-color: var(--acid);
  }}
  .ticket::after {{
    content: "";
    position: absolute;
    top: 0; right: 0;
    width: 0; height: 0;
    border-style: solid;
    border-width: 0 28px 28px 0;
    border-color: transparent var(--ink) transparent transparent;
    filter: drop-shadow(-1px 1px 0 var(--line2));
  }}
  .ticket.LONG {{ box-shadow: inset 4px 0 0 var(--mint); }}
  .ticket.SHORT {{ box-shadow: inset 4px 0 0 var(--hot); }}

  .ticket-top {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 12px;
  }}
  .sym {{
    font-family: var(--display);
    font-weight: 800;
    font-size: 1.35rem;
    letter-spacing: -0.03em;
    line-height: 1;
  }}
  .pills {{ display: flex; flex-wrap: wrap; gap: 6px; justify-content: flex-end; }}
  .pill {{
    font-family: var(--mono);
    font-size: 0.62rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 4px 8px;
    border-radius: 999px;
    border: 1px solid var(--line2);
    color: var(--fog);
  }}
  .pill.LONG {{ color: var(--mint); border-color: rgba(62,240,194,0.4); background: var(--mint-dim); }}
  .pill.SHORT {{ color: var(--hot); border-color: rgba(255,77,154,0.4); background: var(--hot-dim); }}
  .pill.ready {{
    color: var(--acid);
    border-color: rgba(214,255,60,0.45);
    background: var(--acid-dim);
  }}
  .pill.filtered {{
    color: var(--amber);
    border-color: rgba(255,176,32,0.4);
    background: rgba(255,176,32,0.1);
  }}

  .str-row {{
    display: flex;
    align-items: baseline;
    gap: 10px;
    margin-bottom: 6px;
  }}
  .str-num {{
    font-family: var(--display);
    font-weight: 800;
    font-size: 3rem;
    line-height: 0.9;
    letter-spacing: -0.05em;
    color: var(--acid);
  }}
  .str-label {{
    font-family: var(--mono);
    font-size: 0.65rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--fog);
  }}
  .str-label small {{
    display: block;
    margin-top: 4px;
    letter-spacing: 0.04em;
    color: var(--cream2);
    font-size: 0.72rem;
  }}

  .metrics {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px 12px;
    margin: 14px 0 10px;
    font-family: var(--mono);
    font-size: 0.7rem;
    color: var(--fog);
  }}
  .metrics b {{
    color: var(--cream);
    font-weight: 600;
  }}
  .pos {{ color: var(--mint) !important; }}
  .neg {{ color: var(--hot) !important; }}

  .tags {{ display: flex; flex-wrap: wrap; gap: 5px; margin: 8px 0; }}
  .tag {{
    font-family: var(--mono);
    font-size: 0.6rem;
    letter-spacing: 0.04em;
    padding: 3px 7px;
    border-radius: 2px;
    background: var(--violet-dim);
    color: #c4b5fd;
    border: 1px solid rgba(139, 92, 246, 0.25);
  }}

  .reason {{
    font-family: var(--serif);
    font-size: 0.86rem;
    font-style: italic;
    color: var(--fog);
    line-height: 1.4;
    margin-top: 8px;
  }}

  .spark {{
    width: 100%;
    height: 72px;
    margin-top: 12px;
    display: block;
    border-radius: 2px;
    background: rgba(0,0,0,0.25);
  }}

  /* ── controls ── */
  .controls {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    margin-bottom: 14px;
    padding: 12px;
    background: var(--ink2);
    border: 1px dashed var(--line2);
    border-radius: 2px;
  }}
  select, input, button {{
    font-family: var(--mono);
    font-size: 0.72rem;
    background: var(--ink);
    border: 1px solid var(--line2);
    color: var(--cream);
    border-radius: 2px;
    padding: 9px 11px;
  }}
  select:focus, input:focus, button:focus {{
    outline: 2px solid var(--acid);
    outline-offset: 1px;
  }}
  button {{
    cursor: pointer;
    background: var(--acid);
    color: var(--ink);
    border-color: var(--acid);
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }}
  button:hover {{ filter: brightness(1.08); }}

  /* ── board table ── */
  .table-wrap {{
    overflow-x: auto;
    border: 1px solid var(--line2);
    border-radius: 2px;
    background: linear-gradient(180deg, var(--ink2), var(--ink));
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-family: var(--mono);
    font-size: 0.74rem;
  }}
  th {{
    text-align: left;
    padding: 12px 10px;
    font-size: 0.62rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--acid);
    background: rgba(214, 255, 60, 0.06);
    border-bottom: 2px solid var(--acid);
    position: sticky;
    top: 0;
    font-weight: 600;
  }}
  td {{
    padding: 11px 10px;
    border-bottom: 1px solid var(--line);
    color: var(--cream2);
    white-space: nowrap;
  }}
  tr:hover td {{
    background: rgba(139, 92, 246, 0.08);
  }}
  td.sym {{
    font-family: var(--display);
    font-weight: 700;
    font-size: 0.9rem;
    letter-spacing: -0.02em;
    color: var(--cream);
  }}
  td.str {{
    font-family: var(--display);
    font-weight: 800;
    font-size: 1.05rem;
    color: var(--acid);
  }}

  /* ── footer manifesto ── */
  .manifesto {{
    margin-top: 8px;
    padding: 22px 24px;
    background: var(--cream);
    color: var(--ink);
    border-radius: 2px 24px 2px 2px;
    position: relative;
  }}
  .manifesto::before {{
    content: "FIELD NOTES";
    position: absolute;
    top: -10px;
    left: 18px;
    font-family: var(--mono);
    font-size: 0.62rem;
    letter-spacing: 0.16em;
    background: var(--violet);
    color: var(--cream);
    padding: 3px 10px;
  }}
  .manifesto h3 {{
    font-family: var(--display);
    font-weight: 800;
    font-size: 1.1rem;
    letter-spacing: -0.02em;
    text-transform: uppercase;
    margin: 4px 0 12px;
  }}
  .manifesto p {{
    font-family: var(--serif);
    font-size: 0.95rem;
    line-height: 1.55;
    margin: 0 0 8px;
    color: #2a2433;
  }}
  .manifesto .mint {{ color: #0d8f72; font-weight: 600; font-style: normal; }}
  .manifesto .hot {{ color: #c2185b; font-weight: 600; font-style: normal; }}

  footer {{
    margin-top: 28px;
    padding-top: 16px;
    border-top: 1px solid var(--line);
    font-family: var(--mono);
    font-size: 0.65rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--fog);
    display: flex;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
  }}
  footer span {{ color: var(--acid); }}

  .empty {{
    padding: 28px;
    border: 1px dashed var(--line2);
    font-family: var(--serif);
    font-style: italic;
    color: var(--fog);
    background: var(--ink2);
  }}

  @media (max-width: 720px) {{
    .masthead {{ grid-template-columns: 1fr; }}
    .stamp {{ transform: none; justify-self: start; }}
    .str-num {{ font-size: 2.4rem; }}
  }}
</style>
</head>
<body>
<div class="shell">
  <header class="masthead">
    <div>
      <p class="kicker">RJ · Trading for Dickheads · Edition 03</p>
      <h1>Idiot <em>Flow</em><br/>Bourse</h1>
      <p class="deck">
        Mechanical board-path projector. When the tile looks better, idiots bid.
        When it sours, they dump. <strong>We know the tile before they do.</strong>
      </p>
    </div>
    <div class="stamp">
      Live scan
      <b>{n_ad}</b>
      ready
    </div>
  </header>

  <div class="ticker">
    <div class="tick">venue <b>{venue}</b></div>
    <div class="tick">mode <b>{mode}</b></div>
    <div class="tick">as of <b>{generated}</b></div>
    <div class="tick hi">ready <b>{n_ad}</b></div>
    <div class="tick">classic-raw <b>{n_raw}</b></div>
    <div class="tick">ideas <b>{n_ideas}</b></div>
    <div class="tick warn">regime <b>{herd_bias}</b></div>
  </div>
  <p class="lede">{herd_note}</p>

  <section>
    <div class="sec-head">
      <h2>Potato <span>//</span> mouse book</h2>
      <div class="sec-note">adaptive ready · fall back to near-misses</div>
    </div>
    <div class="potato-grid" id="potato"></div>
  </section>

  <section>
    <div class="sec-head">
      <h2>Full <span>//</span> board</h2>
      <div class="sec-note">filter · sort · stare</div>
    </div>
    <div class="controls">
      <select id="sideFilter">
        <option value="ALL">All sides</option>
        <option value="LONG">Longs only</option>
        <option value="SHORT">Shorts only</option>
      </select>
      <select id="stateFilter">
        <option value="ALL">All states</option>
        <option value="READY" selected>READY only</option>
        <option value="FILTERED">FILTERED OUT</option>
        <option value="PATH">PATH / other</option>
      </select>
      <select id="sortBy">
        <option value="score">Sort: score</option>
        <option value="strength">Sort: pine strength</option>
        <option value="delta">Sort: |Δpp|</option>
        <option value="outz">Sort: outgoing z</option>
        <option value="att">Sort: attention</option>
        <option value="vol">Sort: volume</option>
      </select>
      <input id="minStr" type="number" value="0" step="1" placeholder="min strength"/>
      <input id="minVol" type="number" value="0" step="10000" placeholder="min vol"/>
      <button id="apply">Apply</button>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Score</th><th>Str</th><th>State</th><th>Symbol</th><th>Side</th>
            <th>Δpp</th><th>Out%</th><th>zOut</th><th>zEdge</th><th>Att</th><th>RVOL</th>
            <th>Board</th><th>Vol</th><th>Path</th><th>Tags</th>
          </tr>
        </thead>
        <tbody id="tbody"></tbody>
      </table>
    </div>
  </section>

  <section>
    <div class="manifesto">
      <h3>How to read this like a potato</h3>
      <p>
        <span class="mint">LONG</span> when a red extreme rolls off and the board is set to look better.
        <span class="hot">SHORT</span> when a green extreme rolls off and the board sours.
      </p>
      <p>
        <b>READY</b> cleared the Pine adaptive gates. <b>FILTERED OUT</b> is classic raw that failed
        shock / edge / attention / RVOL / trend — almost, not free money.
      </p>
      <p>
        Prefer the potato tickets. Hold through the cliff hour. Fees murder hourly flips.
        Not financial advice — just a mean little mirror of the 24h tile.
      </p>
    </div>
  </section>

  <footer>
    <div>Idiot Flow Bourse · Acid ledger · re-run <span>scanner.py --html</span></div>
    <div>pine adaptive · board path · no prophets</div>
  </footer>
</div>

<script id="payload" type="application/json">{data_json}</script>
<script>
const DATA = JSON.parse(document.getElementById('payload').textContent);

function fmt(n, d=2) {{
  if (n === undefined || n === null || Number.isNaN(n)) return '—';
  return Number(n).toFixed(d);
}}
function fmtVol(v) {{
  if (v >= 1e6) return (v/1e6).toFixed(2) + 'M';
  if (v >= 1e3) return (v/1e3).toFixed(1) + 'k';
  return String(Math.round(v||0));
}}
function cls(n) {{ return n >= 0 ? 'pos' : 'neg'; }}

function sparkline(path, side) {{
  if (!path || path.length < 2) return '';
  const w = 300, h = 72, pad = 6;
  const ys = path.map(p => p.displayed_24h_pct);
  const min = Math.min(...ys), max = Math.max(...ys);
  const span = (max - min) || 1;
  const pts = path.map((p, i) => {{
    const x = pad + (i / (path.length - 1)) * (w - pad*2);
    const y = pad + (1 - (p.displayed_24h_pct - min) / span) * (h - pad*2);
    return [x, y];
  }});
  const d = pts.map((p,i) => (i? 'L':'M') + p[0].toFixed(1) + ',' + p[1].toFixed(1)).join(' ');
  // area under path
  const area = d + ` L${{pts.at(-1)[0]}},${{h-pad}} L${{pts[0][0]}},${{h-pad}} Z`;
  const stroke = side === 'LONG' ? '#3ef0c2' : '#ff4d9a';
  const fill = side === 'LONG' ? 'rgba(62,240,194,0.12)' : 'rgba(255,77,154,0.12)';
  let zero = '';
  if (min <= 0 && max >= 0) {{
    const y0 = pad + (1 - (0 - min) / span) * (h - pad*2);
    zero = `<line x1="${{pad}}" y1="${{y0}}" x2="${{w-pad}}" y2="${{y0}}" stroke="rgba(243,234,215,0.2)" stroke-dasharray="4,4"/>`;
  }}
  return `<svg class="spark" viewBox="0 0 ${{w}} ${{h}}" preserveAspectRatio="none">
    <defs>
      <linearGradient id="g${{side}}" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="${{stroke}}" stop-opacity="0.35"/>
        <stop offset="100%" stop-color="${{stroke}}" stop-opacity="1"/>
      </linearGradient>
    </defs>
    ${{zero}}
    <path d="${{area}}" fill="${{fill}}"/>
    <path d="${{d}}" fill="none" stroke="url(#g${{side}})" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="${{pts[0][0]}}" cy="${{pts[0][1]}}" r="3" fill="#f3ead7" opacity="0.5"/>
    <circle cx="${{pts.at(-1)[0]}}" cy="${{pts.at(-1)[1]}}" r="3.5" fill="${{stroke}}"/>
  </svg>`;
}}

function statePill(s) {{
  if (!s) return '';
  if (s.includes('READY')) return `<span class="pill ready">${{s}}</span>`;
  if (s.includes('FILTERED')) return `<span class="pill filtered">${{s}}</span>`;
  return `<span class="pill">${{s}}</span>`;
}}

function renderPotato() {{
  const el = document.getElementById('potato');
  const list = DATA.potato || [];
  if (!list.length) {{
    el.innerHTML = '<div class="empty">No potato tickets this print. Loosen filters or wait for a juicier roll window.</div>';
    return;
  }}
  el.innerHTML = list.map(i => `
    <article class="ticket ${{i.side}}">
      <div class="ticket-top">
        <div class="sym">${{i.symbol.replace('USDT','')}}<span style="opacity:.35;font-size:.7em">/USDT</span></div>
        <div class="pills">
          ${{statePill(i.setup_state)}}
          <span class="pill ${{i.side}}">${{i.side}}</span>
        </div>
      </div>
      <div class="str-row">
        <div class="str-num">${{fmt(i.strength_pine,0)}}</div>
        <div class="str-label">pine strength
          <small>score ${{fmt(i.score,1)}} · cliff ${{fmt(i.cliff_pp)}}@+${{i.cliff_hour}}h</small>
        </div>
      </div>
      <div class="metrics">
        <div>Δ next <b class="${{cls(i.known_roll_delta_pp)}}">${{fmt(i.known_roll_delta_pp)}}pp</b></div>
        <div>outgoing <b class="${{cls(i.outgoing_return_pct)}}">${{fmt(i.outgoing_return_pct)}}%</b></div>
        <div>z out/edge <b>${{fmt(i.outgoing_z,2)}} / ${{fmt(i.roll_edge_z,2)}}</b></div>
        <div>att / rvol <b>${{fmt(i.attention_rank,0)}}p / ${{fmt(i.rvol,2)}}x</b></div>
        <div>board <b>${{fmt(i.current_24h_pct)}} → ${{fmt(i.flat_next_24h_pct)}}</b></div>
        <div>vol <b>${{fmtVol(i.roll_volume)}}</b></div>
      </div>
      <div class="tags">${{(i.tags||[]).slice(0,7).map(t => `<span class="tag">${{t}}</span>`).join('')}}</div>
      ${{sparkline(i.path, i.side)}}
      <div class="reason">${{i.reason||''}}</div>
    </article>
  `).join('');
}}

function filteredIdeas() {{
  const side = document.getElementById('sideFilter').value;
  const state = document.getElementById('stateFilter').value;
  const sortBy = document.getElementById('sortBy').value;
  const minStr = Number(document.getElementById('minStr').value || 0);
  const minVol = Number(document.getElementById('minVol').value || 0);
  let rows = DATA.ideas.filter(i => {{
    if ((i.strength_pine||0) < minStr) return false;
    if ((i.roll_volume||0) < minVol) return false;
    if (side !== 'ALL' && i.side !== side) return false;
    const st = i.setup_state || '';
    if (state === 'READY' && !st.includes('READY')) return false;
    if (state === 'FILTERED' && !st.includes('FILTERED')) return false;
    if (state === 'PATH' && (st.includes('READY') || st.includes('FILTERED'))) return false;
    return true;
  }});
  const key = {{
    score: i => i.score,
    strength: i => i.strength_pine||0,
    delta: i => Math.abs(i.known_roll_delta_pp||0),
    outz: i => i.outgoing_z||0,
    att: i => i.attention_rank||0,
    vol: i => i.roll_volume||0,
  }}[sortBy];
  rows.sort((a,b) => {{
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
    tb.innerHTML = '<tr><td colspan="15" style="padding:24px;font-family:var(--serif);font-style:italic;color:var(--fog)">No rows match these filters.</td></tr>';
    return;
  }}
  tb.innerHTML = rows.map(i => `
    <tr>
      <td>${{fmt(i.score,1)}}</td>
      <td class="str">${{fmt(i.strength_pine,0)}}</td>
      <td>${{statePill(i.setup_state)}}</td>
      <td class="sym">${{i.symbol}}</td>
      <td><span class="pill ${{i.side}}">${{i.side}}</span></td>
      <td class="${{cls(i.known_roll_delta_pp)}}">${{fmt(i.known_roll_delta_pp)}}</td>
      <td class="${{cls(i.outgoing_return_pct)}}">${{fmt(i.outgoing_return_pct)}}</td>
      <td>${{fmt(i.outgoing_z,2)}}</td>
      <td>${{fmt(i.roll_edge_z,2)}}</td>
      <td>${{fmt(i.attention_rank,0)}}</td>
      <td>${{fmt(i.rvol,2)}}</td>
      <td>${{fmt(i.current_24h_pct)}}→${{fmt(i.flat_next_24h_pct)}}</td>
      <td>${{fmtVol(i.roll_volume)}}</td>
      <td style="min-width:130px">${{sparkline(i.path, i.side)}}</td>
      <td style="max-width:180px;overflow:hidden;text-overflow:ellipsis">${{(i.tags||[]).slice(0,3).join(' · ')}}</td>
    </tr>
  `).join('');
}}

document.getElementById('apply').onclick = renderTable;
['sideFilter','stateFilter','sortBy','minStr','minVol'].forEach(id => {{
  document.getElementById(id).addEventListener('change', renderTable);
}});
renderPotato();
renderTable();
</script>
</body>
</html>
"""
    out_path = Path(out_path)
    out_path.write_text(html, encoding="utf-8")
    return out_path
