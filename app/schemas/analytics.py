from pydantic import BaseModel

from app.models.enums import LeadColour


class AnalyzeRequest(BaseModel):
    top_colours: list[LeadColour] | None = None
    bottom_colours: list[LeadColour] | None = None
    narrate: bool = True


class ApplySuggestionsRequest(BaseModel):
    keys: list[str]  # suggestion keys to append to the project rubric
