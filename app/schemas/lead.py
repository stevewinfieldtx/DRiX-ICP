from pydantic import BaseModel

from app.models.enums import LeadColour, LeadStatus, SpeculativeStatus


class LeadCreate(BaseModel):
    company_name: str
    domain: str | None = None


class LeadOut(BaseModel):
    id: str
    company_name: str
    domain: str | None = None
    score: float | None = None
    colour: LeadColour | None = None
    status: LeadStatus
    signals: dict | None = None
    speculative_status: SpeculativeStatus

    class Config:
        from_attributes = True


class LeadAssign(BaseModel):
    assigned_to: str | None = None
    status: LeadStatus | None = None
