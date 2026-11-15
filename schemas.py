from datetime import date, datetime
from pydantic import BaseModel, Field, field_validator

class TrackCreate(BaseModel):
    origin: str = Field(min_length=3, max_length=3)
    destination: str = Field(min_length=3, max_length=3)
    departure_date: date
    @field_validator("origin", "destination")
    @classmethod
    def uppercase_code(cls, v): return v.upper()

class AlertCreate(TrackCreate):
    target_price: float = Field(gt=0)
    currency: str = "INR"
    email: str | None = None

class FareOut(BaseModel):
    id: int
    origin: str
    destination: str
    airline: str
    departure_date: date
    collected_at: datetime
    price: float
    currency: str
    provider: str
    is_sample: bool
    class Config: from_attributes = True
