from pydantic import BaseModel, validator
from typing import Optional

from utils.globalf import validate_sql_injection

class Card(BaseModel):
    title: str
    description: str

    @validator('title')
    def title_is_not_empty(cls, v):
        if not v:
            raise ValueError('Title is empty')
        return v

    @validator('description')
    def description_is_not_empty(cls, v):
        if not v:
            raise ValueError('Description is empty')
        return v