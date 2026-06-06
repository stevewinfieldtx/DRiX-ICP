"""Section 9 pattern miner.

Compares a TOP cohort (e.g. dark_green + green) against a BOTTOM cohort
(yellow + unqualified) across every flattened speculative_data feature, ranks
the most discriminating signals with real statistics, proposes new rubric
signals, and surfaces 'hidden gems' (low scorers that look like winners).

All numbers are computed deterministically in stats.py. The optional LLM layer
(narrate.py) only rephrases findings that already contain the real figures.
"""
from collections import defaultdict
from dataclasses import dataclass, field

from app.models.enums import LeadColour
from app.services.analytics import stats
from app.services.analytics.flatten import flatten, is_numeric

DEFAULT_TOP = {LeadColour.dark_green, LeadColour.green}
DEFAULT_BOTTOM = {LeadColour.yellow, LeadColour.unqualified}

# evidence guards so we never crow about noise
MIN_COHORT = 5            # need at least this many leads per cohort
MIN_SUPPORT = 3           # a trait/value must appear at least this often
SIG_P = 0.10              # categorical significance threshold
MIN_ABS_DIFF = 0.15       # >=15 percentage-point prevalence gap
MIN_ABS_D = 0.4           # numeric effect-size threshold


@dataclass
class Finding:
    feature: str
    kind: str               # "categorical" | "numeric"
    detail: dict
    effect: float           # magnitude used for ranking
    direction: str          # "top" (assoc. with winners) | "bottom"
    headline: str


@dataclass
class MinerResult:
    top_n: int
    bottom_n: int
    findings: list[Finding] = field(default_factory=list)
    suggested_signals: list[dict] = field(default_factory=list)
    hidden_gems: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _flat_for(lead) -> dict:
    return flatten(lead.speculative_data or {})


def mine(leads: list, top_colours=None, bottom_colours=None) -> MinerResult:
    top_colours = top_colours or DEFAULT_TOP
    bottom_colours = bottom_colours or DEFAULT_BOTTOM

    top = [lead for lead in leads if lead.colour in top_colours]
    bottom = [lead for lead in leads if lead.colour in bottom_colours]
    result = MinerResult(top_n=len(top), bottom_n=len(bottom))

    if len(top) < MIN_COHORT or len(bottom) < MIN_COHORT:
        result.notes.append(
            f"Need >= {MIN_COHORT} scored leads in each cohort to mine reliably "
            f"(have top={len(top)}, bottom={len(bottom)}). Score more leads."
        )
        return result

    top_flat = [_flat_for(le) for le in top]
    bottom_flat = [_flat_for(le) for le in bottom]

    numeric_feats, categorical_feats = _feature_universe(top_flat + bottom_flat)

    for feat in numeric_feats:
        f = _numeric_finding(feat, top_flat, bottom_flat)
        if f:
            result.findings.append(f)
    for feat in categorical_feats:
        result.findings.extend(_categorical_findings(feat, top_flat, bottom_flat))

    result.findings.sort(key=lambda f: f.effect, reverse=True)
    result.suggested_signals = _suggest_signals(result.findings)
    result.hidden_gems = _hidden_gems(result.findings, bottom)
    return result


def _feature_universe(all_flat: list[dict]) -> tuple[set, set]:
    numeric, categorical = set(), set()
    sample_vals = defaultdict(list)
    for row in all_flat:
        for k, v in row.items():
            sample_vals[k].append(v)
    for k, vals in sample_vals.items():
        if any(is_numeric(v) for v in vals):
            numeric.add(k)
        else:
            categorical.add(k)
    return numeric, categorical


def _numeric_finding(feat, top_flat, bottom_flat) -> Finding | None:
    a = [r[feat] for r in top_flat if is_numeric(r.get(feat))]
    b = [r[feat] for r in bottom_flat if is_numeric(r.get(feat))]
    if len(a) < MIN_SUPPORT or len(b) < MIN_SUPPORT:
        return None
    res = stats.cohens_d(a, b)
    d = res["d"]
    if d is None or abs(d) < MIN_ABS_D:
        return None
    direction = "top" if d > 0 else "bottom"
    comp = "higher" if d > 0 else "lower"
    headline = (
        f"Winners average {res['mean_a']} vs {res['mean_b']} on '{feat}' "
        f"({comp} among top leads; effect d={d})."
    )
    return Finding(feat, "numeric", res, abs(d), direction, headline)


def _categorical_findings(feat, top_flat, bottom_flat) -> list[Finding]:
    values = {r[feat] for r in top_flat + bottom_flat if feat in r}
    findings = []
    for val in values:
        succ_a = sum(1 for r in top_flat if r.get(feat) == val)
        succ_b = sum(1 for r in bottom_flat if r.get(feat) == val)
        if succ_a + succ_b < MIN_SUPPORT:
            continue
        res = stats.two_proportion_test(succ_a, len(top_flat), succ_b, len(bottom_flat))
        diff, p = res["diff"], res["p_value"]
        if diff is None or abs(diff) < MIN_ABS_DIFF or (p is not None and p > SIG_P):
            continue
        direction = "top" if diff > 0 else "bottom"
        label = f"{feat}={val}"
        pct_a, pct_b = round(res["p_a"] * 100), round(res["p_b"] * 100)
        headline = (
            f"{label}: {pct_a}% of top leads vs {pct_b}% of bottom "
            f"(+{round(diff * 100)}pp, p={p}, lift x{res['lift']})."
            if direction == "top" else
            f"{label}: {pct_a}% of top vs {pct_b}% of bottom "
            f"({round(diff * 100)}pp, p={p}) — more common among weak leads."
        )
        res = {**res, "feature": feat, "value": val}
        findings.append(Finding(label, "categorical", res, abs(diff), direction, headline))
    return findings


def _suggest_signals(findings: list[Finding], limit: int = 8) -> list[dict]:
    """Turn the strongest TOP-associated findings into proposed rubric signals."""
    suggestions = []
    for f in findings:
        if f.direction != "top":
            continue
        # suggested weight scaled by effect (5-20), rounded to nearest 5
        weight = max(5, min(20, round((f.effect * 40) / 5) * 5))
        key = f.feature.replace(".", "_").replace(":", "_").replace(" ", "_").lower()
        suggestions.append({
            "key": key,
            "label": _humanize(f.feature),
            "suggested_weight": weight,
            "type": "boolean" if f.kind == "categorical" else "range",
            "evidence": f.detail,
            "rationale": f.headline,
        })
        if len(suggestions) >= limit:
            break
    return suggestions


def _hidden_gems(findings: list[Finding], bottom_leads: list, limit: int = 10) -> list[dict]:
    """Low scorers that share the winning traits — worth a second look."""
    winning = [f for f in findings if f.direction == "top"][:12]
    if not winning:
        return []
    gems = []
    for lead in bottom_leads:
        flat = _flat_for(lead)
        matched = []
        for f in winning:
            if f.kind == "categorical" and flat.get(f.detail.get("feature")) == f.detail.get("value"):
                matched.append(f.feature)
            elif f.kind == "numeric" and is_numeric(flat.get(f.feature)):
                if flat[f.feature] >= f.detail.get("mean_a", 0):
                    matched.append(f.feature)
        if matched:
            gems.append({
                "lead_id": str(lead.id),
                "company_name": lead.company_name,
                "current_score": float(lead.score) if lead.score is not None else None,
                "current_colour": lead.colour.value if lead.colour else None,
                "winning_traits_matched": matched,
                "match_strength": round(len(matched) / len(winning), 2),
            })
    gems.sort(key=lambda g: g["match_strength"], reverse=True)
    return gems[:limit]


def _humanize(feature: str) -> str:
    return feature.split(".")[-1].replace("_", " ").replace(":", ": ").title()
