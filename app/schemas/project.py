from pydantic import BaseModel

from app.models.enums import Tier


class ProjectCreate(BaseModel):
    name: str
    tier: Tier = Tier.light


class ProjectOut(BaseModel):
    id: str
    name: str
    tier: Tier
    rubric: dict | None = None

    class Config:
        from_attributes = True
