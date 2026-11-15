from datetime import datetime, date
from sqlalchemy import String, Float, Integer, Date, DateTime, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

class FareObservation(Base):
    __tablename__ = "fare_observations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    origin: Mapped[str] = mapped_column(String(3), index=True)
    destination: Mapped[str] = mapped_column(String(3), index=True)
    airline: Mapped[str] = mapped_column(String(80), default="Unknown")
    departure_date: Mapped[date] = mapped_column(Date, index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    provider: Mapped[str] = mapped_column(String(30), default="demo")
    is_sample: Mapped[bool] = mapped_column(Boolean, default=True)

Index("ix_route_date_collected", FareObservation.origin, FareObservation.destination,
      FareObservation.departure_date, FareObservation.collected_at)

class RouteTrack(Base):
    __tablename__ = "route_tracks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    origin: Mapped[str] = mapped_column(String(3))
    destination: Mapped[str] = mapped_column(String(3))
    departure_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class PriceAlert(Base):
    __tablename__ = "price_alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    origin: Mapped[str] = mapped_column(String(3))
    destination: Mapped[str] = mapped_column(String(3))
    departure_date: Mapped[date] = mapped_column(Date)
    target_price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
