# FarePulse — Airfare Intelligence

FarePulse is a full-stack airfare research prototype with flight-offer search, route tracking, fare history, target-price alerts, a route-wise index, and CSV export.

## Data transparency

- Demo mode is enabled by default. Demo prices are generated sample records and are labelled as sample data.
- To request provider-backed offers, configure Amadeus credentials and set `FARE_PROVIDER=amadeus`.
- Provider coverage and prices depend on your Amadeus account and environment. Test-environment results are not guaranteed bookable prices.
- FarePulse is a research prototype, not an official Consumer Price Index or a guaranteed cheapest-fare service.

## Deploy the complete app to Vercel

The repository keeps the React/Vite frontend and FastAPI backend together. Vercel serves the frontend build and routes `/api/*` requests to the Python function in `api/index.py`.

### 1. Import the repository

1. Push or merge the deployment branch into GitHub.
2. Open [Vercel New Project](https://vercel.com/new).
3. Import `vedantrandive02/FarePulse`.
4. Keep the project root set to the repository root (do not select a subfolder).
5. Vercel should use the included `vercel.json` build command and `dist` output directory.

### 2. Add a persistent PostgreSQL database

Vercel function filesystems are not a persistent database. Create a managed PostgreSQL database (for example, Neon or Supabase) and copy its connection string.

In Vercel → Project → Settings → Environment Variables, add:

| Variable | Value |
|---|---|
| `DATABASE_URL` | Your PostgreSQL URL. Prefer `postgresql+psycopg://...`; `postgres://` and `postgresql://` are normalized automatically. |
| `FARE_PROVIDER` | `demo` initially, or `amadeus` when credentials are ready |
| `CORS_ORIGINS` | Your Vercel deployment origin, e.g. `https://your-project.vercel.app` |
| `SCHEDULER_ENABLED` | `false` |
| `SECRET_KEY` | A long, random secret |
| `AMADEUS_CLIENT_ID` | Only required for Amadeus |
| `AMADEUS_CLIENT_SECRET` | Only required for Amadeus |
| `AMADEUS_BASE_URL` | `https://test.api.amadeus.com` for testing |

Do not commit real credentials or a real `.env` file. Leave `VITE_API_URL` unset when frontend and API share the same Vercel domain.

### 3. Deploy

Save the environment variables, then trigger a new deployment from the Vercel Deployments tab. After it finishes, test:

- `https://YOUR-PROJECT.vercel.app/`
- `https://YOUR-PROJECT.vercel.app/api/health`
- `https://YOUR-PROJECT.vercel.app/docs`

The health endpoint should return `status: ok`. The first API invocation creates the database tables.

### Serverless behavior

Vercel functions do not keep an in-process scheduler running between requests. Fare observations are therefore collected when users search; the built-in APScheduler is disabled by default. A persistent PostgreSQL database is required to retain searches, tracks, alerts, and history across deployments and function instances. The optional email field on alerts is metadata only; email delivery is not configured.

## Run locally

Requirements: Python 3.12 and Node.js 20 or later.

### Backend

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

API docs: http://127.0.0.1:8000/docs

### Frontend

In another terminal:

```bash
npm install
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` requests to the local backend on port 8000.

## Enable Amadeus

Set the following environment variables in your backend environment:

```env
FARE_PROVIDER=amadeus
AMADEUS_CLIENT_ID=your_client_id
AMADEUS_CLIENT_SECRET=your_client_secret
AMADEUS_BASE_URL=https://test.api.amadeus.com
```

Never expose Amadeus credentials in frontend variables or commit them to GitHub.

## Docker Compose (optional local setup)

The root Docker setup runs the React frontend, FastAPI API, and PostgreSQL locally:

```bash
docker compose up --build
```

Frontend: http://localhost:5173  
API docs: http://localhost:8000/docs

## API endpoints

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

For each route and departure date, the index compares the current average observed fare with the average fare from the earliest collection date:

`index = (current average / baseline average) × 100`

An index of 110 means the observed average is 10% above that route/date baseline. The index is only as representative as the recorded observations.
