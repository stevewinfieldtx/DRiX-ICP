"""Import all models so Alembic autogenerate and metadata see them."""
from app.db.base import Base
from app.models.api_key import ApiKey
from app.models.document import Document
from app.models.lead import Lead
from app.models.project import Project
from app.models.user import User

__all__ = ["Base", "ApiKey", "Document", "Lead", "Project", "User"]
