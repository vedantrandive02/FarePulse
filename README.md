# FarePulse — Airfare Intelligence & Price Tracking

FarePulse is a full-stack airfare monitoring and research prototype. It provides route search, fare history, target-price alerts, a route-wise airfare index, CSV exports, and scheduled collection.

## Important data transparency
- **Demo mode is enabled by default.** Demo fares are generated sample records and are visibly labelled as sample data in the UI.
- For actual provider-backed fares, configure Amadeus credentials and set `FARE_PROVIDER=amadeus`. Availability, coverage, and pricing depend on your provider account and API environment.
- This is a research prototype, not an official Consumer Price Index or a guaranteed cheapest-fare service.
- FarePulse stores observations returned by the configured provider. It does not bypass airline websites, CAPTCHAs, or access restrictions.

## Features
- Search fares by origin, destination, departure date, and passenger count.
- Track a route/date and inspect historical recorded observations.
- Set target-price alerts; alert checks run when new observations are collected.
- Explore a baseline-normalized route index.
- Export observations and index data as CSV.
- Scheduled collection using APScheduler.
- FastAPI Swagger docs at `/docs`.
- SQLite by default; PostgreSQL supported through `DATABASE_URL`.
- Docker Compose setup.

## Quick start (local)

Requirements: Python 3.11+, Node.js 20+.

### 1. Backend
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload
```
API: http://localhost:8000  
Docs: http://localhost:8000/docs

### 2. Frontend
In another terminal:
```bash
npm install
npm run dev
```
Open http://localhost:5173

## Enable Amadeus API
1. Create an API app at https://developers.amadeus.com/.
2. Copy the API key and secret into `.env`.
3. Set `FARE_PROVIDER=amadeus`.
4. Restart the backend.

```env
FARE_PROVIDER=amadeus
AMADEUS_CLIENT_ID=your_client_id
AMADEUS_CLIENT_SECRET=your_client_secret
AMADEUS_BASE_URL=https://test.api.amadeus.com
```
The test environment is for development and may not reflect production inventory or final bookable prices. Never commit `.env` or API secrets.

## Docker
From the repository root:
```bash
docker compose up --build
```
Frontend: http://localhost:5173  
Backend: http://localhost:8000/docs

## API overview
- `GET /api/health`
- `GET /api/dashboard`
- `GET /api/fares/search?origin=DEL&destination=BOM&departure_date=2026-12-15&adults=1`
- `GET /api/routes/{origin}/{destination}/history?departure_date=2026-12-15`
- `POST /api/tracks`
- `GET /api/tracks`
- `DELETE /api/tracks/{track_id}`
- `POST /api/alerts`
- `GET /api/alerts`
- `DELETE /api/alerts/{alert_id}`
- `GET /api/research/index`
- `GET /api/research/export.csv`

## Index methodology
For each route and departure date, the index compares the average observed fare with the average fare in the earliest available collection date (the baseline).  
`index = (current average / baseline average) × 100`.  
An index of 110 means the observed average is 10% above that route/date baseline. Results are only as representative as the collected observations. The baseline and observation counts are exposed in the research view.

## GitHub
Create a new empty GitHub repository, then:
```bash
git init
git add .
git commit -m "Build FarePulse airfare tracking platform"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

## Production checklist
- Use a managed PostgreSQL database.
- Set a strong `SECRET_KEY` and restrict CORS to your deployed frontend domain.
- Add HTTPS and secret management.
- Use a production Amadeus account or another permitted data provider.
- Configure email/SMS delivery for alerts if required (the current version exposes in-app alert status).
- Deploy the frontend and API separately or use the included Docker setup.
- Review provider terms, rate limits, data retention, and redistribution permissions.
