from datetime import date, datetime
import random
import httpx
from config import settings

class AmadeusProvider:
    def __init__(self):
        self.token = None
        self.token_expires = 0

    async def _access_token(self):
        if self.token and datetime.utcnow().timestamp() < self.token_expires - 30:
            return self.token
        if not settings.amadeus_client_id or not settings.amadeus_client_secret:
            raise RuntimeError("Amadeus credentials are missing. Configure backend/.env.")
        async with httpx.AsyncClient(timeout=25) as client:
            response = await client.post(
                f"{settings.amadeus_base_url}/v1/security/oauth2/token",
                data={"grant_type": "client_credentials",
                      "client_id": settings.amadeus_client_id,
                      "client_secret": settings.amadeus_client_secret},
                headers={"Content-Type": "application/x-www-form-urlencoded"})
            response.raise_for_status()
            data = response.json()
        self.token = data["access_token"]
        self.token_expires = datetime.utcnow().timestamp() + int(data.get("expires_in", 1700))
        return self.token

    async def search(self, origin: str, destination: str, departure_date: date, adults: int = 1):
        token = await self._access_token()
        params = {"originLocationCode": origin, "destinationLocationCode": destination,
                  "departureDate": departure_date.isoformat(), "adults": adults,
                  "currencyCode": "INR", "max": 30}
        async with httpx.AsyncClient(timeout=35) as client:
            response = await client.get(f"{settings.amadeus_base_url}/v2/shopping/flight-offers",
                params=params, headers={"Authorization": f"Bearer {token}"})
            response.raise_for_status()
            payload = response.json()
        results = []
        dictionaries = payload.get("dictionaries", {}).get("carriers", {})
        for offer in payload.get("data", []):
            itineraries = offer.get("itineraries", [])
            segments = itineraries[0].get("segments", []) if itineraries else []
            airline_code = segments[0].get("carrierCode", "Unknown") if segments else "Unknown"
            results.append({"origin": origin, "destination": destination,
                "airline": dictionaries.get(airline_code, airline_code),
                "departure_date": departure_date, "price": float(offer["price"]["grandTotal"]),
                "currency": offer["price"].get("currency", "INR"),
                "provider": "amadeus", "is_sample": False})
        return results

def demo_fares(origin: str, destination: str, departure_date: date, count: int = 12):
    seed = sum(map(ord, origin + destination + departure_date.isoformat()))
    rng = random.Random(seed)
    base = rng.randint(2800, 9500)
    airlines = ["IndiGo", "Air India", "Akasa Air", "SpiceJet", "Vistara"]
    rows = []
    for i in range(count):
        rows.append({"origin": origin, "destination": destination,
            "airline": airlines[i % len(airlines)], "departure_date": departure_date,
            "price": round(base * rng.uniform(.86, 1.19), 2), "currency": "INR",
            "provider": "demo", "is_sample": True})
    return rows

class SerpapiProvider:
    def __init__(self):
        if not settings.serpapi_api_key:
            raise RuntimeError("SerpAPI key is missing. Set SERPAPI_API_KEY in .env.")

    async def search(self, origin: str, destination: str, departure_date: date, adults: int = 1):
        params = {
            "engine": "google_flights",
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": departure_date.isoformat(),
            "currency": "INR",
            "hl": "en",
            "api_key": settings.serpapi_api_key,
        }
        async with httpx.AsyncClient(timeout=35) as client:
            response = await client.get(settings.serpapi_base_url, params=params)
            response.raise_for_status()
            payload = response.json()

        results = []

        def extract_flights(flight_group):
            items = []
            for f in flight_group:
                price = f.get("price")
                if price is None:
                    continue
                flights = f.get("flights", [])
                if not flights:
                    continue
                first = flights[0]
                airline = first.get("airline", "Unknown")
                items.append({
                    "origin": origin,
                    "destination": destination,
                    "airline": airline,
                    "departure_date": departure_date,
                    "price": float(price),
                    "currency": "INR",
                    "provider": "serpapi",
                    "is_sample": False,
                })
            return items

        results.extend(extract_flights(payload.get("best_flights", [])))
        results.extend(extract_flights(payload.get("other_flights", [])))

        # Fallback: try to read top-level flights if best_flights/other_flights missing
        if not results:
            for f in payload.get("flights", []):
                price = f.get("price")
                if price is None:
                    continue
                results.append({
                    "origin": origin,
                    "destination": destination,
                    "airline": f.get("airline", "Unknown"),
                    "departure_date": departure_date,
                    "price": float(price),
                    "currency": "INR",
                    "provider": "serpapi",
                    "is_sample": False,
                })

        return results


async def search_fares(origin, destination, departure_date, adults=1):
    provider = settings.fare_provider.lower()
    if provider == "amadeus":
        return await AmadeusProvider().search(origin, destination, departure_date, adults)
    if provider == "serpapi":
        return await SerpapiProvider().search(origin, destination, departure_date, adults)
    return demo_fares(origin, destination, departure_date)
