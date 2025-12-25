from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

class Product(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = ""
    price: float = Field(..., ge=0.0)
    qty: int = Field(0, ge=0)
    category: Optional[str] = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ProductPatch(BaseModel):
    # Частичное обновление: все поля опциональны
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(None, ge=0.0)
    qty: Optional[int] = Field(None, ge=0)
    category: Optional[str] = None
