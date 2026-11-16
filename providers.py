from datetime import date, datetime
import random
import httpx
from config import settings

class AmadeusProvider:
    def __init__(self):
        self.token = None
        self.token_expires = 0

    async def _access_token(self):
        now = datetime.utcnow().timestamp()
        if self.token and now < self.token_expires - 30:
            return self.token
        if not settings.amadeus_client_id or not settings.amadeus_client_secret:
            raise RuntimeError("Amadeus credentials are not configured.")
        async with httpx.AsyncClient(timeout=25) as client:
            response = await client.post(
                f"{settings.amadeus_base_url.rstrip('/')}/v1/security/oauth2/token",
                data={"grant_type": "client_credentials", "client_id": settings.amadeus_client_id,
                      "client_secret": settings.amadeus_client_secret},
                headers={"Content-Type": "application/x-www-form-urlencoded"})
            response.raise_for_status()
            data = response.json()
        self.token = data["access_token"]
        self.token_expires = now + int(data.get("expires_in", 1700))
        return self.token

    async def search(self, origin: str, destination: str, departure_date: date, adults: int = 1):
        token = await self._access_token()
        params = {"originLocationCode": origin, "destinationLocationCode": destination,
                  "departureDate": departure_date.isoformat(), "adults": adults,
                  "currencyCode": "INR", "max": 30}
        async with httpx.AsyncClient(timeout=35) as client:
            response = await client.get(
                f"{settings.amadeus_base_url.rstrip('/')}/v2/shopping/flight-offers",
                params=params, headers={"Authorization": f"Bearer {token}"})
            response.raise_for_status()
            payload = response.json()
        carriers = payload.get("dictionaries", {}).get("carriers", {})
        results = []
        for offer in payload.get("data", []):
            itineraries = offer.get("itineraries", [])
            segments = itineraries[0].get("segments", []) if itineraries else []
            code = segments[0].get("carrierCode", "Unknown") if segments else "Unknown"
            results.append({"origin": origin, "destination": destination,
                "airline": carriers.get(code, code), "departure_date": departure_date,
                "price": float(offer["price"]["grandTotal"]),
                "currency": offer["price"].get("currency", "INR"),
                "provider": "amadeus", "is_sample": False})
        return results

def demo_fares(origin: str, destination: str, departure_date: date, count: int = 12):
    seed = sum(map(ord, origin + destination + departure_date.isoformat()))
    rng = random.Random(seed)
    base = rng.randint(2800, 9500)
    airlines = ["IndiGo", "Air India", "Akasa Air", "SpiceJet", "Vistara"]
    return [{"origin": origin, "destination": destination, "airline": airlines[i % len(airlines)],
        "departure_date": departure_date, "price": round(base * rng.uniform(.86, 1.19), 2),
        "currency": "INR", "provider": "demo", "is_sample": True} for i in range(count)]

async def search_fares(origin, destination, departure_date, adults=1):
    if settings.fare_provider.lower() == "amadeus":
        return await AmadeusProvider().search(origin, destination, departure_date, adults)
    return demo_fares(origin, destination, departure_date)
