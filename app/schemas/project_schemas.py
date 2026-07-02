"""Schémas Pydantic : projets (portfolio)."""
import datetime as dt
import json
from typing import Optional

from pydantic import BaseModel, field_validator


class ProjectCreate(BaseModel):
    title: str
    client_name: Optional[str] = None
    description: Optional[str] = None
    preview_image_path: Optional[str] = None
    technologies: Optional[str] = None
    external_link: Optional[str] = None
    completion_date: Optional[dt.date] = None
    is_published: bool = False


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    client_name: Optional[str] = None
    description: Optional[str] = None
    preview_image_path: Optional[str] = None
    technologies: Optional[str] = None
    external_link: Optional[str] = None
    completion_date: Optional[dt.date] = None
    is_published: Optional[bool] = None
    display_order: Optional[str] = None


class ProjectOut(BaseModel):
    id: str
    title: str
    client_name: Optional[str] = None
    description: Optional[str] = None
    preview_image_path: Optional[str] = None
    gallery_images: list[str] = []
    video_url: Optional[str] = None
    technologies: Optional[str] = None
    external_link: Optional[str] = None
    completion_date: Optional[dt.date] = None
    is_published: bool
    display_order: str
    created_at: dt.datetime

    @field_validator("gallery_images", mode="before")
    @classmethod
    def _parse_gallery(cls, v):
        if v is None:
            return []
        ids = v
        if isinstance(v, str):
            try:
                ids = json.loads(v)
            except (ValueError, TypeError):
                ids = []
        return [f"/api/files/{file_id}" for file_id in ids]

    class Config:
        from_attributes = True
