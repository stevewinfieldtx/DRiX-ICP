import enum


class Tier(str, enum.Enum):
    light = "light"   # Level 1 - LLM-only
    deep = "deep"     # Level 2 - API-enriched + speculative capture


class LeadColour(str, enum.Enum):
    dark_green = "dark_green"
    green = "green"
    yellow = "yellow"
    unqualified = "unqualified"


class LeadStatus(str, enum.Enum):
    new = "new"
    assigned = "assigned"
    contacted = "contacted"
    disqualified = "disqualified"


class DocumentStatus(str, enum.Enum):
    uploaded = "uploaded"
    extracting = "extracting"
    extracted = "extracted"
    failed = "failed"


class SpeculativeStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    complete = "complete"
    partial = "partial"
    failed = "failed"
