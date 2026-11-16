from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from statistics import mean
import csv, io, logging
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import settings
from database import Base, engine, get_db, SessionLocal
from models import FareObservation, RouteTrack, PriceAlert
from schemas import TrackCreate, AlertCreate
from providers import search_fares

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("farepulse")
scheduler = AsyncIOScheduler(timezone="UTC")

async def collect_for_track(track_id: int | None = None):
    db = SessionLocal()
    try:
        q = db.query(RouteTrack)
        if track_id:
            q = q.filter(RouteTrack.id == track_id)
        tracks = q.all()
        for track in tracks:
            try:
                fares = await search_fares(track.origin, track.destination, track.departure_date)
                for item in fares:
                    db.add(FareObservation(**item, collected_at=datetime.utcnow()))
                db.commit()
                check_alerts(db, track.origin, track.destination, track.departure_date,
                             min([x["price"] for x in fares], default=None))
            except Exception as exc:
                db.rollback()
                log.exception("Collection failed for track %s: %s", track.id, exc)
    finally:
        db.close()

def check_alerts(db, origin, destination, departure_date, lowest):
    if lowest is None: return
    alerts = db.query(PriceAlert).filter_by(origin=origin, destination=destination,
        departure_date=departure_date, active=True, triggered=False).all()
    for alert in alerts:
        if lowest <= alert.target_price:
            alert.triggered = True
            log.info("PRICE ALERT TRIGGERED: %s-%s %s at %s %s (alert %s)",
                origin, destination, departure_date, lowest, alert.currency, alert.id)
    db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    if settings.scheduler_enabled and settings.collection_interval_minutes > 0:
        scheduler.add_job(collect_for_track, "interval",
            minutes=settings.collection_interval_minutes, id="fare_collection",
            replace_existing=True, max_instances=1)
        scheduler.start()
    yield
    if scheduler.running: scheduler.shutdown(wait=False)

app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan,
              description="Airfare tracking and research prototype. Demo data is labelled.")
app.add_middleware(CORSMiddleware, allow_origins=settings.origins,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/api/health")
def health():
    return {"status": "ok", "provider": settings.fare_provider,
            "data_mode": "sample" if settings.fare_provider == "demo" else "provider"}

@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    total = db.query(FareObservation).count()
    routes = db.query(RouteTrack).count()
    alerts = db.query(PriceAlert).count()
    latest = db.query(func.max(FareObservation.collected_at)).scalar()
    return {"observations": total, "tracked_routes": routes, "alerts": alerts,
            "last_updated": latest, "provider": settings.fare_provider,
            "sample_mode": settings.fare_provider == "demo"}

@app.get("/api/fares/search")
async def fare_search(origin: str = Query(min_length=3, max_length=3),
    destination: str = Query(min_length=3, max_length=3),
    departure_date: date = Query(), adults: int = Query(1, ge=1, le=9),
    db: Session = Depends(get_db)):
    origin, destination = origin.upper(), destination.upper()
    if origin == destination: raise HTTPException(400, "Origin and destination must differ.")
    try:
        fares = await search_fares(origin, destination, departure_date, adults)
    except Exception as exc:
        log.exception("Fare provider request failed")
        raise HTTPException(502, "Fare provider request failed. Check provider settings and try again.")
    for item in fares:
        db.add(FareObservation(**item, collected_at=datetime.utcnow()))
    db.commit()
    check_alerts(db, origin, destination, departure_date,
                 min([x["price"] for x in fares], default=None))
    return {"fares": fares, "count": len(fares),
            "sample_mode": bool(fares and fares[0]["is_sample"]),
            "message": "Sample data for demonstration." if fares and fares[0]["is_sample"] else "Provider results recorded."}

@app.get("/api/routes/{origin}/{destination}/history")
def route_history(origin: str, destination: str, departure_date: date,
                  db: Session = Depends(get_db)):
    rows = db.query(FareObservation).filter(
        FareObservation.origin == origin.upper(),
        FareObservation.destination == destination.upper(),
        FareObservation.departure_date == departure_date
    ).order_by(FareObservation.collected_at.asc()).all()
    return [{"id": r.id, "collected_at": r.collected_at, "price": r.price,
             "airline": r.airline, "currency": r.currency, "is_sample": r.is_sample}
            for r in rows]

@app.post("/api/tracks")
async def create_track(payload: TrackCreate, db: Session = Depends(get_db)):
    if payload.origin == payload.destination: raise HTTPException(400, "Choose two different airports.")
    existing = db.query(RouteTrack).filter_by(origin=payload.origin,
        destination=payload.destination, departure_date=payload.departure_date).first()
    if existing: return {"id": existing.id, "message": "Route already tracked."}
    track = RouteTrack(**payload.model_dump())
    db.add(track); db.commit(); db.refresh(track)
    # Fare observations are recorded by explicit searches; serverless requests must stay short.
    return {"id": track.id, "message": "Route tracking started."}

@app.get("/api/tracks")
def list_tracks(db: Session = Depends(get_db)):
    return [{"id": x.id, "origin": x.origin, "destination": x.destination,
             "departure_date": x.departure_date, "created_at": x.created_at}
            for x in db.query(RouteTrack).order_by(RouteTrack.created_at.desc()).all()]

@app.delete("/api/tracks/{track_id}")
def delete_track(track_id: int, db: Session = Depends(get_db)):
    track = db.get(RouteTrack, track_id)
    if not track: raise HTTPException(404, "Track not found.")
    db.delete(track); db.commit()
    return {"message": "Tracking stopped."}

@app.post("/api/alerts")
def create_alert(payload: AlertCreate, db: Session = Depends(get_db)):
    alert = PriceAlert(**payload.model_dump())
    db.add(alert); db.commit(); db.refresh(alert)
    return {"id": alert.id, "message": "Target alert created."}

@app.get("/api/alerts")
def list_alerts(db: Session = Depends(get_db)):
    return [{"id": a.id, "origin": a.origin, "destination": a.destination,
        "departure_date": a.departure_date, "target_price": a.target_price,
        "currency": a.currency, "email": a.email, "active": a.active,
        "triggered": a.triggered} for a in db.query(PriceAlert).order_by(PriceAlert.created_at.desc()).all()]

@app.delete("/api/alerts/{alert_id}")
def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.get(PriceAlert, alert_id)
    if not alert: raise HTTPException(404, "Alert not found.")
    db.delete(alert); db.commit()
    return {"message": "Alert deleted."}

@app.get("/api/research/index")
def research_index(db: Session = Depends(get_db)):
    rows = db.query(FareObservation).order_by(FareObservation.collected_at.asc()).all()
    grouped = {}
    for r in rows:
        key = (r.origin, r.destination, r.departure_date.isoformat(), r.currency)
        grouped.setdefault(key, []).append(r)
    result = []
    for (origin, destination, travel_date, currency), observations in grouped.items():
        by_day = {}
        for obs in observations:
            by_day.setdefault(obs.collected_at.date().isoformat(), []).append(obs.price)
        days = sorted(by_day)
        baseline = mean(by_day[days[0]]) if days else 0
        current = mean(by_day[days[-1]]) if days else 0
        result.append({"origin": origin, "destination": destination,
            "departure_date": travel_date, "currency": currency,
            "baseline_date": days[0] if days else None,
            "current_date": days[-1] if days else None,
            "baseline_average": round(baseline, 2),
            "current_average": round(current, 2),
            "index": round(current / baseline * 100, 2) if baseline else None,
            "observations": len(observations),
            "sample_data": any(x.is_sample for x in observations)})
    return result

@app.get("/api/research/export.csv")
def export_csv(db: Session = Depends(get_db)):
    rows = db.query(FareObservation).order_by(FareObservation.collected_at.asc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["origin","destination","airline","departure_date","collected_at",
                     "price","currency","provider","is_sample"])
    for r in rows:
        writer.writerow([r.origin,r.destination,r.airline,r.departure_date,
            r.collected_at.isoformat(),r.price,r.currency,r.provider,r.is_sample])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=farepulse-observations.csv"})
