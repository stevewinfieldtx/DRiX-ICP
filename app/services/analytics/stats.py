"""Dependency-free statistics for cohort comparison.

Kept pure and small so the numbers in every recommendation are deterministic and
auditable (no LLM-invented figures). Significance is approximate but honest, and
always reported alongside sample sizes so weak evidence is visible.
"""
import math


def normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def two_proportion_test(succ_a: int, n_a: int, succ_b: int, n_b: int) -> dict:
    """Compare prevalence of a trait between cohort A (top) and B (bottom).

    Returns prevalences, percentage-point difference, lift ratio, z and a
    two-sided p-value (normal approximation). None-safe on empty cohorts.
    """
    if n_a == 0 or n_b == 0:
        return {"p_a": None, "p_b": None, "diff": None, "lift": None,
                "z": None, "p_value": None, "n_a": n_a, "n_b": n_b}
    p_a, p_b = succ_a / n_a, succ_b / n_b
    p_pool = (succ_a + succ_b) / (n_a + n_b)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))
    z = (p_a - p_b) / se if se > 0 else 0.0
    p_value = 2 * (1 - normal_cdf(abs(z)))
    lift = (p_a / p_b) if p_b > 0 else (math.inf if p_a > 0 else None)
    return {
        "p_a": round(p_a, 4), "p_b": round(p_b, 4),
        "diff": round(p_a - p_b, 4),
        "lift": (round(lift, 2) if lift not in (None, math.inf) else lift),
        "z": round(z, 3), "p_value": round(p_value, 4),
        "n_a": n_a, "n_b": n_b,
    }


def mean_sd(values: list[float]) -> tuple[float, float, int]:
    n = len(values)
    if n == 0:
        return 0.0, 0.0, 0
    mean = sum(values) / n
    if n == 1:
        return mean, 0.0, 1
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    return mean, math.sqrt(var), n


def cohens_d(a: list[float], b: list[float]) -> dict:
    """Standardized mean difference between numeric cohorts."""
    m_a, sd_a, n_a = mean_sd(a)
    m_b, sd_b, n_b = mean_sd(b)
    if n_a < 2 or n_b < 2:
        return {"mean_a": round(m_a, 3) if n_a else None,
                "mean_b": round(m_b, 3) if n_b else None,
                "d": None, "n_a": n_a, "n_b": n_b}
    pooled = math.sqrt(((n_a - 1) * sd_a ** 2 + (n_b - 1) * sd_b ** 2) / (n_a + n_b - 2))
    d = (m_a - m_b) / pooled if pooled > 0 else 0.0
    return {"mean_a": round(m_a, 3), "mean_b": round(m_b, 3),
            "d": round(d, 3), "n_a": n_a, "n_b": n_b}
