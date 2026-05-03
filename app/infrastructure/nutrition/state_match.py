"""Infer preparation hints from USDA-style names and score vs requested state."""

from __future__ import annotations

import re
from typing import Iterable


def infer_states_from_candidate_name(candidate_name: str) -> set[str]:
    """Heuristic tags implied by the nutrition.csv description."""
    n = candidate_name.lower()
    out: set[str] = set()
    if re.search(r"\braw\b", n) or ", raw" in n or " raw," in n:
        out.add("raw")
    if "uncooked" in n or "unprepared" in n or re.search(r"\bdry\b", n) or "dry mix" in n:
        out.add("dry")
    if "cooked" in n or "cooked," in n or ", cooked" in n:
        out.add("cooked")
    if "boiled" in n or "steamed" in n or "simmered" in n:
        out.add("boiled")
        out.add("cooked")
    if "fried" in n or "pan-fried" in n or "pan fried" in n:
        out.add("fried")
    if "baked" in n:
        out.add("baked")
    if "grilled" in n:
        out.add("grilled")
    if "roasted" in n:
        out.add("roasted")
    if "canned" in n or "drained solids" in n:
        out.add("canned")
    if "flour" in n or "powder" in n or "dry mix" in n:
        out.add("dry")
    if re.search(r"\bfresh\b", n):
        out.add("raw")
    return out


def _has_any(hay: str, needles: Iterable[str]) -> bool:
    h = hay.lower()
    return any(x in h for x in needles)


def _query_implies_flour_powder(query: str) -> bool:
    q = query.lower()
    return any(w in q for w in ("flour", "powder", "mix", "meal", "starch"))


def state_score(
    requested_state: str,
    candidate_name: str,
    *,
    query: str,
    is_grain_like: bool,
) -> tuple[float, list[str]]:
    """
    Returns (score_adjustment, reason strings).
    Text similarity is handled elsewhere; this is additive state alignment.
    """
    rs = (requested_state or "unknown").strip().lower()
    n = candidate_name.lower()
    reasons: list[str] = []

    cooked_soft = ("cooked", "boiled", "steamed", "simmered")
    cooked_hard = ("baked", "grilled", "roasted", "fried", "pan-fried", "pan fried")
    canned_markers = ("canned", "drained solids")

    def add(score: float, reason: str) -> None:
        nonlocal reasons
        reasons.append(f"{score:+.0f}:{reason}")

    score = 0.0

    if rs == "unknown":
        return 0.0, reasons

    has_dry = _has_any(n, ("dry", "uncooked", "unprepared", "unenriched")) or "flour" in n or "powder" in n
    has_raw = bool(re.search(r"\braw\b", n)) or "fresh" in n
    has_cooked = any(x in n for x in cooked_soft) or any(x in n for x in cooked_hard)
    has_boiled = "boiled" in n
    has_fried = "fried" in n or "pan-fried" in n
    has_baked = "baked" in n
    has_grilled = "grilled" in n
    has_roasted = "roasted" in n
    has_canned = any(x in n for x in canned_markers)

    if rs == "cooked":
        if any(x in n for x in cooked_soft):
            score += 30
            add(30, "cooked/boiled/steamed")
        elif any(x in n for x in cooked_hard):
            score += 20
            add(20, "baked/grilled/roasted/fried")
        elif has_dry or has_raw:
            score -= 45
            add(-45, "dry/raw/unprepared")
        elif not has_cooked:
            score += 10
            add(10, "no explicit state")
        if has_dry and not _query_implies_flour_powder(query) and any(w in n for w in ("flour", "powder", "mix")):
            score -= 25
            add(-25, "flour/powder vs non-flour query")
        if is_grain_like and (has_dry or "uncooked" in n or "unprepared" in n):
            score -= 30
            add(-30, "grain cooked vs dry row")

    elif rs == "boiled":
        if has_boiled:
            score += 35
            add(35, "boiled")
        elif "cooked" in n or "steamed" in n:
            score += 25
            add(25, "cooked-like")
        elif has_dry or has_raw:
            score -= 40
            add(-40, "dry/raw/unprepared")
        if has_fried or has_grilled or has_baked or has_roasted:
            score -= 15
            add(-15, "fried/grilled/baked/roasted")

    elif rs == "fried":
        if has_fried:
            score += 35
            add(35, "fried")
        elif "cooked" in n:
            score += 15
            add(15, "cooked")
        elif has_dry or has_raw or "unprepared" in n:
            score -= 35
            add(-35, "raw/dry/unprepared")
        if has_boiled:
            score -= 10
            add(-10, "boiled")

    elif rs == "baked":
        if has_baked:
            score += 35
            add(35, "baked")
        elif "cooked" in n:
            score += 15
            add(15, "cooked")
        elif has_dry or has_raw or "unprepared" in n:
            score -= 35
            add(-35, "raw/dry/unprepared")

    elif rs == "grilled":
        if has_grilled:
            score += 35
            add(35, "grilled")
        elif "cooked" in n:
            score += 15
            add(15, "cooked")
        elif has_dry or has_raw or "unprepared" in n:
            score -= 35
            add(-35, "raw/dry/unprepared")

    elif rs == "roasted":
        if has_roasted:
            score += 35
            add(35, "roasted")
        elif "cooked" in n:
            score += 20
            add(20, "cooked")
        elif has_dry or has_raw or "unprepared" in n:
            score -= 35
            add(-35, "raw/dry/unprepared")

    elif rs == "raw":
        if re.search(r"\braw\b", n) or ", raw" in n:
            score += 35
            add(35, "raw")
        elif "fresh" in n:
            score += 15
            add(15, "fresh")
        if has_cooked or has_boiled or has_fried or has_baked or has_grilled or has_roasted:
            score -= 35
            add(-35, "cooked family")
        if has_canned or has_dry or "unprepared" in n:
            score -= 20
            add(-20, "canned/dry/unprepared")

    elif rs == "dry":
        if has_dry or "uncooked" in n or "unprepared" in n:
            score += 35
            add(35, "dry/uncooked")
        if _query_implies_flour_powder(query) and any(w in n for w in ("flour", "powder", "mix")):
            score += 20
            add(20, "flour/powder aligned")
        if "cooked" in n or has_boiled:
            score -= 35
            add(-35, "cooked/boiled")
        if has_canned:
            score -= 20
            add(-20, "canned")

    elif rs == "canned":
        if has_canned:
            score += 40
            add(40, "canned")
        if "solids and liquids" in n or "drained" in n:
            score += 15
            add(15, "packaged liquid/solids")
        if has_raw or has_dry:
            score -= 30
            add(-30, "raw/dry")

    return score, reasons
