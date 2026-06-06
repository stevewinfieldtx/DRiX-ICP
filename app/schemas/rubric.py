"""Shape of a generated ICP rubric stored on Project.rubric.

{
  "version": 1,
  "signals": [
    {
      "key": "industry",
      "label": "Industry fit",
      "weight": 15,
      "type": "categorical",
      "good_values": ["SaaS", "Cybersecurity"],
      "description": "..."
    },
    {"key": "employee_count", "label": "Company size", "weight": 10, "type": "range",
     "ideal_min": 50, "ideal_max": 1000}
  ],
  "thresholds": {"dark_green": 80, "green": 60, "yellow": 40}
}
"""
from pydantic import BaseModel


class RubricSignal(BaseModel):
    key: str
    label: str
    weight: float
    type: str = "categorical"
    description: str | None = None


class Rubric(BaseModel):
    version: int = 1
    signals: list[RubricSignal] = []
    thresholds: dict[str, float] = {"dark_green": 80, "green": 60, "yellow": 40}
