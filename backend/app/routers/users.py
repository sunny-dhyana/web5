import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import get_password_hash, verify_password
from app.database import get_db
from app.models.user import User
from app.schemas.user import ChangePasswordRequest, UpdateProfileRequest, UserResponse

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_profile(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.full_name is not None:
        current_user.full_name = body.full_name
    if body.bio is not None:
        current_user.bio = body.bio
    if body.profile_picture_url is not None:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(body.profile_picture_url, timeout=5, follow_redirects=True)
            content_type = resp.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                raise HTTPException(
                    status_code=400,
                    detail=f"URL does not point to a valid image (content-type: {content_type}): {resp.text[:300]}"
                )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=400, detail=f"Could not fetch image URL: {exc}")
        current_user.profile_picture_url = body.profile_picture_url

    if body.role is not None:
        current_user.role = body.role
    if body.is_verified is not None:
        current_user.is_verified = body.is_verified

    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/me/password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    current_user.hashed_password = get_password_hash(body.new_password)
    db.commit()

    return {"message": "Password updated successfully"}


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_public(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
