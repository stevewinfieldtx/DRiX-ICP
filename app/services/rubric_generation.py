"""Generate an ICP rubric from solution materials (Section 6)."""
from app.services.llm import chat_json

_SYSTEM = (
    "You are an expert B2B go-to-market analyst. Given a vendor's solution materials, "
    "produce an Ideal Customer Profile scoring rubric as JSON. Output an object with keys: "
    "'version' (int), 'signals' (array of {key, label, weight, type, description}; weights "
    "should sum to ~100), and 'thresholds' ({dark_green, green, yellow}). "
    "Signal 'type' is one of categorical|range|boolean."
)

_FALLBACK = {
    "version": 1,
    "signals": [
        {"key": "industry", "label": "Industry fit", "weight": 25, "type": "categorical",
         "description": "Target vertical alignment"},
        {"key": "employee_count", "label": "Company size", "weight": 20, "type": "range",
         "description": "Headcount in ideal band"},
        {"key": "tech_stack", "label": "Tech stack fit", "weight": 20, "type": "boolean",
         "description": "Uses complementary tooling"},
        {"key": "growth_signals", "label": "Growth signals", "weight": 20, "type": "boolean",
         "description": "Hiring / funding momentum"},
        {"key": "region", "label": "Region", "weight": 15, "type": "categorical",
         "description": "Served geography"},
    ],
    "thresholds": {"dark_green": 80, "green": 60, "yellow": 40},
}


async def generate(corpus: str) -> dict:
    user = f"Solution materials:\n\n{corpus[:16000]}"
    result = await chat_json(_SYSTEM, user)
    if not result or "signals" not in result:
        # Keep MVP usable without an API key configured.
        return _FALLBACK
    result.setdefault("version", 1)
    result.setdefault("thresholds", {"dark_green": 80, "green": 60, "yellow": 40})
    return result
