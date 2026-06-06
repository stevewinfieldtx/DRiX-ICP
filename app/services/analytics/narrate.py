"""Optional natural-language summary of miner findings.

The LLM only PHRASES findings that already contain real, computed numbers — it
never invents figures. Falls back to a deterministic summary with no API key.
"""
from app.services.analytics.patterns import MinerResult
from app.services.llm import chat_json

_SYSTEM = (
    "You are a revenue-operations analyst. You are given pre-computed statistical "
    "findings comparing high-fit vs low-fit leads. Summarize the 3-5 most actionable "
    "insights in plain English for a sales leader. Do NOT invent numbers; only use the "
    "figures provided. Return JSON: {'summary': str, 'top_insights': [str, ...]}."
)


def deterministic_summary(result: MinerResult) -> dict:
    top = [f.headline for f in result.findings if f.direction == "top"][:5]
    return {
        "summary": (
            f"Compared {result.top_n} high-fit vs {result.bottom_n} low-fit leads. "
            f"Found {len(result.findings)} discriminating signals; "
            f"{len(result.suggested_signals)} proposed as new rubric signals; "
            f"{len(result.hidden_gems)} hidden gems flagged."
        ),
        "top_insights": top or ["No signal cleared the evidence thresholds yet."],
    }


async def narrate(result: MinerResult) -> dict:
    fallback = deterministic_summary(result)
    if not result.findings:
        return fallback
    payload = {
        "cohorts": {"top_n": result.top_n, "bottom_n": result.bottom_n},
        "findings": [f.headline for f in result.findings[:15]],
        "suggested_signals": [s["label"] for s in result.suggested_signals],
    }
    out = await chat_json(_SYSTEM, str(payload))
    return out if out.get("summary") else fallback
