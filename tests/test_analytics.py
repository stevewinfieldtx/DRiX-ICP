"""Tests for the Section 9 pattern miner (pure / no DB / no network)."""
from dataclasses import dataclass

from app.models.enums import LeadColour
from app.services.analytics import patterns, stats


# ---- stats ----
def test_two_proportion_basic():
    r = stats.two_proportion_test(18, 20, 4, 20)  # 90% vs 20%
    assert r["diff"] == 0.7
    assert r["lift"] == 4.5
    assert r["p_value"] < 0.01


def test_two_proportion_empty_cohort():
    r = stats.two_proportion_test(0, 0, 3, 10)
    assert r["diff"] is None


def test_cohens_d_direction():
    r = stats.cohens_d([10, 11, 9, 12, 10], [2, 3, 1, 2, 2])
    assert r["d"] > 1.0  # large positive effect
    assert r["mean_a"] > r["mean_b"]


# ---- end-to-end miner on synthetic leads ----
@dataclass
class FakeLead:
    id: str
    company_name: str
    score: float
    colour: LeadColour
    speculative_data: dict


def _make(colour, has_weak_dmarc, ratio, name, score):
    return FakeLead(
        id=name, company_name=name, score=score, colour=colour,
        speculative_data={
            "dns": {"dmarc_policy": "none" if has_weak_dmarc else "reject"},
            "derived": {"ratios": {"technical_to_sales_ratio": ratio}},
        },
    )


def _dataset():
    leads = []
    # winners: weak dmarc + low tech:sales ratio
    for i in range(8):
        leads.append(_make(LeadColour.dark_green, True, 0.4, f"win{i}", 90))
    # losers: strong dmarc + high tech:sales ratio
    for i in range(8):
        leads.append(_make(LeadColour.unqualified, False, 2.0, f"lose{i}", 20))
    # a hidden gem: scored low, but looks like a winner
    leads.append(_make(LeadColour.unqualified, True, 0.4, "gem", 25))
    return leads


def test_miner_finds_discriminating_signal():
    result = patterns.mine(_dataset())
    assert result.top_n == 8
    feats = {f.feature for f in result.findings}
    # the weak-dmarc trait should surface as associated with winners
    assert any("dmarc_policy=none" in f for f in feats)
    assert any(s["key"].startswith("dns_dmarc_policy") for s in result.suggested_signals)


def test_miner_flags_hidden_gem():
    result = patterns.mine(_dataset())
    gem_names = {g["company_name"] for g in result.hidden_gems}
    assert "gem" in gem_names


def test_miner_needs_minimum_cohort():
    tiny = [
        FakeLead("a", "a", 90, LeadColour.dark_green, {}),
        FakeLead("b", "b", 10, LeadColour.unqualified, {}),
    ]
    result = patterns.mine(tiny)
    assert result.findings == []
    assert result.notes  # explains why
