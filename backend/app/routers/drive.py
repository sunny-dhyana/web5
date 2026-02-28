import os
import shutil
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.drive import DriveFile
from app.schemas.drive import DriveFileResponse
from app.core.deps import get_current_user

router = APIRouter()

DRIVE_UPLOAD_DIR = os.path.join("data", "drive_uploads")
os.makedirs(DRIVE_UPLOAD_DIR, exist_ok=True)

def get_drive_user(current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.seller, UserRole.admin]:
        raise HTTPException(status_code=403, detail="Drive access is restricted to sellers.")
    return current_user

@router.post("/upload", response_model=DriveFileResponse)
def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_drive_user),
    db: Session = Depends(get_db)
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    ext = os.path.splitext(file.filename)[1] if file.filename else ""
    safe_filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(DRIVE_UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    size = os.path.getsize(file_path)

    drive_file = DriveFile(
        seller_id=current_user.id,
        file_name=file.filename or "unnamed_file",
        file_path=file_path,
        content_type=file.content_type,
        size=size
    )
    db.add(drive_file)
    db.commit()
    db.refresh(drive_file)
    return drive_file

@router.get("", response_model=List[DriveFileResponse])
def list_files(
    current_user: User = Depends(get_drive_user),
    db: Session = Depends(get_db)
):
    files = db.query(DriveFile).filter(DriveFile.seller_id == current_user.id).all()
    return files

@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    current_user: User = Depends(get_drive_user),
    db: Session = Depends(get_db)
):
    drive_file = db.query(DriveFile).filter(DriveFile.id == file_id, DriveFile.seller_id == current_user.id).first()
    if not drive_file:
        raise HTTPException(status_code=404, detail="File not found")

    if not os.path.exists(drive_file.file_path):
        raise HTTPException(status_code=404, detail="File missing on disk")

    return FileResponse(
        path=drive_file.file_path,
        filename=drive_file.file_name,
        media_type=drive_file.content_type
    )

@router.delete("/{file_id}")
def delete_file(
    file_id: int,
    current_user: User = Depends(get_drive_user),
    db: Session = Depends(get_db)
):
    drive_file = db.query(DriveFile).filter(DriveFile.id == file_id, DriveFile.seller_id == current_user.id).first()
    if not drive_file:
        raise HTTPException(status_code=404, detail="File not found")

    if os.path.exists(drive_file.file_path):
        os.remove(drive_file.file_path)

    db.delete(drive_file)
    db.commit()
    return {"status": "success", "detail": "File deleted"}
