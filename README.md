# Idiot Flow Bourse

Cross-sectional crypto scanner for the **24h return roll-off** edge
(Robot James / *Trading for Dickheads*), with filters ported from
`RJ_24H_Roll_Off_Adaptive_v2.pine`.

## Live board

**→ [Open the Idiot Flow Lab](https://21e8-miner.github.io/idiot-flow-bourse/)**

Snapshot of the adaptive potato book + full board (Acid Bourse UI).
Re-run the scanner locally (or via Actions) to refresh.

## What it does

Exchanges plaster **24h %** everywhere. Part of that number is mechanical:
the reference price walks forward. If price is flat, we can project how the
tile will look. Retail piles into “looking good” and dumps “looking bad.”

| Setup | Bias |
|-------|------|
| Largest **red** bar rolling out of the 24h window | **LONG** |
| Largest **green** bar rolling out | **SHORT** |

Plus Pine-style adaptive filters: shock z, edge z, attention percentile, RVOL, trend veto.

## Run locally

```bash
python scanner.py --html --open
python scanner.py --min-shock-z 1.0 --min-attention 40 --min-rvol 0.3 --html --open
python scanner.py --mode explore --venue okx
```

Python 3.10+, **no pip deps**.

| File | Role |
|------|------|
| `scanner.py` | CLI, venues, watch mode |
| `engine.py` | Pine math + board path + scoring |
| `dashboard.py` | Acid Bourse HTML generator |
| `index.html` | GitHub Pages live board |
| `RJ_24H_Roll_Off_Adaptive_v2.pine` | TradingView reference strategy |

## Modes

- `adaptive` — classic window-extreme (READY + FILTERED OUT)
- `classic` — READY only
- `explore` — also path-only drifts

## Disclaimer

Research / education only. Not financial advice. Crypto is violent;
dumb-money patterns can die; you can lose money.
