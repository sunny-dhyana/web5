from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class DriveFileResponse(BaseModel):
    id: int
    seller_id: int
    file_name: str
    content_type: Optional[str]
    size: int
    created_at: datetime

    class Config:
        from_attributes = True
