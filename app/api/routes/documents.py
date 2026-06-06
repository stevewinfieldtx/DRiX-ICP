import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.models.project import Project
from app.models.user import User
from app.services import text_extraction

router = APIRouter(prefix="/projects/{project_id}/documents", tags=["documents"])


@router.post("")
async def upload_document(
    project_id: uuid.UUID,
    file: UploadFile,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = db.get(Project, project_id)
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    raw = await file.read()
    doc = Document(
        project_id=project_id,
        filename=file.filename or "upload",
        content_type=file.content_type,
        status=DocumentStatus.extracting,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Synchronous extraction for MVP; move to worker for large files.
    try:
        doc.extracted_text = text_extraction.extract(raw, file.content_type, file.filename)
        doc.status = DocumentStatus.extracted
    except Exception:  # noqa: BLE001
        doc.status = DocumentStatus.failed
    db.commit()

    return {"id": str(doc.id), "status": doc.status.value, "chars": len(doc.extracted_text or "")}
