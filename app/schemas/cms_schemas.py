"""Schémas Pydantic : CMS (contenu, FAQ, tarifs)."""
import datetime as dt
import json
from typing import Optional

from pydantic import BaseModel, field_validator


class ContentBlockOut(BaseModel):
    key: str
    label: Optional[str] = None
    value: str
    content_type: str
    updated_at: dt.datetime

    class Config:
        from_attributes = True


class ContentBlockUpdate(BaseModel):
    value: str


class FaqEntryCreate(BaseModel):
    question: str
    answer: str
    display_order: int = 0
    is_published: bool = True


class FaqEntryUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    display_order: Optional[int] = None
    is_published: Optional[bool] = None


class FaqEntryOut(BaseModel):
    id: str
    question: str
    answer: str
    display_order: int
    is_published: bool

    class Config:
        from_attributes = True


class PricingPlanCreate(BaseModel):
    name: str
    price: str
    features: list[str] = []
    is_featured: bool = False
    display_order: int = 0
    is_published: bool = True


class PricingPlanUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[str] = None
    features: Optional[list[str]] = None
    is_featured: Optional[bool] = None
    display_order: Optional[int] = None
    is_published: Optional[bool] = None


class PricingPlanOut(BaseModel):
    id: str
    name: str
    price: str
    features: list[str]
    is_featured: bool
    display_order: int
    is_published: bool

    @field_validator("features", mode="before")
    @classmethod
    def parse_features(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return []
        return v

    class Config:
        from_attributes = True


class RepeatableItemCreate(BaseModel):
    group_key: str
    fields: dict = {}
    display_order: int = 0
    is_published: bool = True


class RepeatableItemUpdate(BaseModel):
    fields: Optional[dict] = None
    display_order: Optional[int] = None
    is_published: Optional[bool] = None


class RepeatableItemOut(BaseModel):
    id: str
    group_key: str
    fields: dict
    display_order: int
    is_published: bool

    @field_validator("fields", mode="before")
    @classmethod
    def parse_fields(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return {}
        return v

    class Config:
        from_attributes = True


class RepeatableItemReorder(BaseModel):
    ordered_ids: list[str]
