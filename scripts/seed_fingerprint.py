#!/usr/bin/env python3
"""Seed .board-fingerprint from current index.html (same logic as CI)."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
html_path = ROOT / "index.html"
html = html_path.read_text(encoding="utf-8")
m = re.search(
    r'<script id="payload" type="application/json">(.*?)</script>',
    html,
    re.S,
)
if not m:
    sys.exit("payload missing from index.html")
data = json.loads(m.group(1))
meta = dict(data.get("meta") or {})
for k in ("generated_at", "elapsed_s"):
    meta.pop(k, None)
ideas = data.get("ideas") or []
compact = []
for idea in ideas:
    compact.append(
        {
            "symbol": idea.get("symbol"),
            "side": idea.get("side"),
            "roll_open_time": idea.get("roll_open_time"),
            "setup_state": idea.get("setup_state"),
            "adaptive_pass": bool(idea.get("adaptive_pass")),
            "score_bin": round(float(idea.get("score") or 0), 1),
            "next_drift_bin": round(float(idea.get("next_drift_pp") or 0), 2),
        }
    )
compact.sort(key=lambda x: (x.get("symbol") or "", x.get("side") or ""))
blob = json.dumps(
    {
        "meta_mode": meta.get("mode"),
        "meta_venue": meta.get("venue"),
        "n_ideas": meta.get("n_ideas"),
        "n_adaptive": meta.get("n_adaptive"),
        "herd": meta.get("herd"),
        "ideas": compact,
    },
    sort_keys=True,
    separators=(",", ":"),
)
fp = hashlib.sha256(blob.encode()).hexdigest()[:16]
out = ROOT / ".board-fingerprint"
out.write_text(fp + "\n", encoding="utf-8")
print("seeded", out, fp)
