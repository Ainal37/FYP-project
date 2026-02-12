"""
Unified Risk Scoring Engine
────────────────────────────
Combines: heuristic detector + threat intel + NLP message analysis.
Output: score 0-100, threat_level LOW/MED/HIGH, explainable breakdown.
"""

import json
from typing import Optional

from .detector import heuristic_scan
from .intel import query_all as intel_query_all
from .nlp import analyze_message


def compute_risk_score(
    link: str,
    message: Optional[str] = None,
    skip_intel: bool = False,
) -> dict:
    """
    Compute a unified risk score for a URL (and optional message).

    Returns dict with:
        score, threat_level, verdict, breakdown, intel_summary, reason
    """
    breakdown: list = []

    # 1. Heuristic analysis
    h = heuristic_scan(link)
    breakdown.extend(h["breakdown"])

    # 2. Threat intelligence
    intel_summary = {}
    if not skip_intel:
        try:
            intel = intel_query_all(link)
            breakdown.extend(intel["breakdown"])
            intel_summary = intel.get("summary", {})
        except Exception:
            pass  # Graceful: intel failure must never block scan

    # 3. NLP (if message provided)
    if message and message.strip():
        try:
            nlp = analyze_message(message)
            breakdown.extend(nlp["breakdown"])
        except Exception:
            pass

    # Aggregate
    total = min(sum(b["points"] for b in breakdown), 100)

    if total >= 55:
        threat_level = "HIGH"
        verdict = "scam"
    elif total >= 25:
        threat_level = "MED"
        verdict = "suspicious"
    else:
        threat_level = "LOW"
        verdict = "safe"

    reason = "; ".join(b["detail"] for b in breakdown if b.get("detail")) or "No red flags"

    return {
        "score": total,
        "threat_level": threat_level,
        "verdict": verdict,
        "breakdown": breakdown,
        "intel_summary": intel_summary,
        "reason": reason,
    }
