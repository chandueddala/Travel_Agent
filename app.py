from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Optional, TypedDict, List, Dict, Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from fastapi import FastAPI, HTTPException
from typing_extensions import Annotated
from pydantic import BaseModel, Field, StringConstraints
from pydantic_settings import BaseSettings

# Optional LLM (used only if OPENAI_API_KEY present)
try:
    from langgraph.graph import StateGraph, END
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI
except Exception:  # pragma: no cover
    StateGraph = END = ChatOpenAI = None  # allow code to run without these libs


# =========================
# Settings (env-driven)
# =========================
class Settings(BaseSettings):
    OPENAI_API_KEY: Optional[str] = None
    TICKETMASTER_API_KEY: Optional[str] = None
    REQUEST_TIMEOUT_SECONDS: int = 8
    MAX_RETRIES: int = 3
    MODEL_NAME: str = "gpt-4o-mini"
    MODEL_TEMPERATURE: float = 0.2

    class Config:
        env_file = ".env"

settings = Settings()


# =========================
# HTTP helpers (retry)
# =========================
class ExternalError(RuntimeError): ...
def _timeout() -> httpx.Timeout: return httpx.Timeout(settings.REQUEST_TIMEOUT_SECONDS)

HEADERS_WIKI = {"User-Agent": "TripPlanner/1.0 (github.com/example)"}

@retry(
    reraise=True,
    stop=stop_after_attempt(settings.MAX_RETRIES),
    wait=wait_exponential(multiplier=0.6, min=0.5, max=4),
    retry=retry_if_exception_type(ExternalError),
)
async def _get_json(client: httpx.AsyncClient, url: str, *, headers: Dict[str, str] | None = None, params: Dict[str, Any] | None = None) -> Any:
    try:
        r = await client.get(url, headers=headers, params=params, timeout=_timeout())
        if r.status_code >= 500:
            raise ExternalError(f"Server error {r.status_code}")
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as e:
        code = getattr(e.response, "status_code", None)
        if code == 404:
            raise
        raise ExternalError(str(e)) from e


# =========================
# I/O Schemas
# =========================
class TripRequest(BaseModel):
    destination: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2)] = Field(..., example="Paris, France")
    days: Annotated[int, Field(ge=1, le=21, example=4)]


class POI(BaseModel):
    name: str
    summary: Optional[str] = None
    distance_km: Optional[float] = None
    url: Optional[str] = None


class Event(BaseModel):
    title: str
    start_local: str
    venue: Optional[str] = None
    url: Optional[str] = None


class WeatherDaily(BaseModel):
    date: str
    temp_day_c: float
    temp_night_c: float
    condition: str
    precipitation_mm: float


class DayPlan(BaseModel):
    day: int
    date: str
    morning: str
    afternoon: str
    evening: str
    meals: List[str]


class TripResponse(BaseModel):
    destination: str
    days: int
    summary: str
    daily_itinerary: List[DayPlan]
    packing_list: Dict[str, List[str]]
    context: Dict[str, Any]


# =========================
# Free providers
# =========================
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
WIKI_SEARCH_URL = "https://{lang}.wikipedia.org/w/api.php"
TICKETMASTER_URL = "https://app.ticketmaster.com/discovery/v2/events.json"

async def geocode(client: httpx.AsyncClient, place: str) -> dict:
    params = {"name": place, "count": 1, "language": "en", "format": "json"}
    data = await _get_json(client, GEOCODE_URL, params=params)
    results = data.get("results") or []
    if not results:
        raise HTTPException(status_code=404, detail="Destination not found")
    top = results[0]
    return {
        "name": top.get("name"),
        "country": top.get("country"),
        "lat": top["latitude"],
        "lon": top["longitude"],
        "timezone": top.get("timezone") or "UTC",
    }

async def forecast(client: httpx.AsyncClient, lat: float, lon: float, days: int, timezone: str) -> List[WeatherDaily]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": timezone,
    }
    data = await _get_json(client, FORECAST_URL, params=params)
    daily = data.get("daily") or {}
    dates = daily.get("time", [])
    maxs = daily.get("temperature_2m_max", [])
    mins = daily.get("temperature_2m_min", [])
    precs = daily.get("precipitation_sum", [])
    codes = daily.get("weathercode", [])
    def code_to_text(c:int)->str:
        # simple mapping (Open-Meteo codes)
        if c in (0,): return "Clear"
        if c in (1,2,3): return "Partly cloudy"
        if c in (45,48): return "Fog"
        if c in (51,53,55,56,57): return "Drizzle"
        if c in (61,63,65,66,67): return "Rain"
        if c in (71,73,75,77): return "Snow"
        if c in (80,81,82): return "Rain showers"
        if c in (85,86): return "Snow showers"
        if c in (95,96,99): return "Thunderstorm"
        return "Mixed"
    out: List[WeatherDaily] = []
    for i, d in enumerate(dates[:days]):
        out.append(WeatherDaily(
            date=d,
            temp_day_c=float(maxs[i]),
            temp_night_c=float(mins[i]),
            precipitation_mm=float(precs[i]),
            condition=code_to_text(int(codes[i]))
        ))
    return out

async def wiki_pois(client: httpx.AsyncClient, lat: float, lon: float, radius_m: int = 3000, max_items: int = 8, lang: str = "en") -> List[POI]:
    # 1) GeoSearch for nearby pages
    params = {
        "action": "query",
        "list": "geosearch",
        "gscoord": f"{lat}|{lon}",
        "gsradius": radius_m,
        "gslimit": max_items,
        "format": "json"
    }
    base = WIKI_SEARCH_URL.format(lang=lang)
    geo = await _get_json(client, base, headers=HEADERS_WIKI, params=params)
    pages = geo.get("query", {}).get("geosearch", [])
    if not pages:
        return []
    pageids = [str(p["pageid"]) for p in pages]
    # 2) Extract summaries
    params2 = {
        "action": "query",
        "prop": "extracts|info",
        "pageids": "|".join(pageids),
        "exintro": 1,
        "explaintext": 1,
        "inprop": "url",
        "format": "json"
    }
    det = await _get_json(client, base, headers=HEADERS_WIKI, params=params2)
    pages_det = (det.get("query", {}).get("pages") or {}).values()
    out: List[POI] = []
    for p in pages_det:
        name = p.get("title")
        summary = (p.get("extract") or "").strip()
        url = p.get("fullurl")
        # distance if present from first result set
        dkm = None
        for g in pages:
            if g["pageid"] == p["pageid"]:
                dkm = round(g.get("dist", 0.0) / 1000.0, 2)
                break
        out.append(POI(name=name, summary=summary[:600], url=url, distance_km=dkm))
    return out

async def ticketmaster_events(client: httpx.AsyncClient, lat: float, lon: float, start: datetime, end: datetime, radius_km: int = 25) -> List[Event]:
    if not settings.TICKETMASTER_API_KEY:
        return []
    params = {
        "apikey": settings.TICKETMASTER_API_KEY,
        "latlong": f"{lat},{lon}",
        "radius": radius_km,
        "unit": "km",
        "locale": "*",
        "startDateTime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endDateTime": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "size": 20,
        "sort": "date,asc",
    }
    data = await _get_json(client, TICKETMASTER_URL, params=params)
    events = data.get("_embedded", {}).get("events", [])
    out: List[Event] = []
    for e in events:
        title = e.get("name")
        url = e.get("url")
        dates = e.get("dates", {}).get("start", {})
        start_local = dates.get("localDate") or dates.get("dateTime") or ""
        venue = None
        ev = e.get("_embedded", {}).get("venues", [])
        if ev:
            venue = ev[0].get("name")
        out.append(Event(title=title, start_local=start_local, venue=venue, url=url))
    return out


# =========================
# Itinerary + packing logic (deterministic)
# =========================
def summarize_context(dest_label: str, forecast_days: List[WeatherDaily], pois: List[POI], events: List[Event]) -> str:
    if not forecast_days:
        weather_line = "Weather: (not available)"
    else:
        first = forecast_days[0]
        temps = f"{first.temp_day_c:.0f}/{first.temp_night_c:.0f}°C"
        weather_line = f"First day looks {first.condition.lower()}, {temps} with {first.precipitation_mm:.0f}mm precip."
    return f"{dest_label}: {weather_line}. {len(pois)} sights nearby, {len(events)} events found."

def plan_blocks(day_idx: int, date_str: str, pois: List[POI], events: List[Event]) -> DayPlan:
    # simple rotation through POIs; slot an event in evening if available
    poi_m = pois[(day_idx * 3 + 0) % max(1, len(pois))]["name"] if pois else "Neighborhood walk"
    poi_a = pois[(day_idx * 3 + 1) % max(1, len(pois))]["name"] if len(pois) > 1 else "Museum or gallery"
    evening_ev = events[day_idx] if day_idx < len(events) else None
    eve_text = f"Attend: {evening_ev.title} @ {evening_ev.venue}" if evening_ev else (pois[(day_idx * 3 + 2) % max(1, len(pois))]["name"] if len(pois) > 2 else "Food market & riverfront")
    meals = ["Local bakery breakfast", "Regional specialty lunch", "Well-reviewed dinner spot"]
    return DayPlan(
        day=day_idx + 1,
        date=date_str,
        morning=f"Explore: {poi_m}",
        afternoon=f"Visit: {poi_a}",
        evening=eve_text,
        meals=meals
    )

def build_packing_list(forecast_days: List[WeatherDaily]) -> Dict[str, List[str]]:
    essentials = ["Passport/ID", "Wallet", "Phone + charger", "Meds", "Reusable bottle"]
    clothing = ["Walking shoes", "Socks/underwear", "Tops/bottoms"]
    toiletries = ["Toothbrush/toothpaste", "Deodorant", "Sunscreen"]
    electronics = ["Power adapter", "Power bank"]

    if forecast_days:
        hot = any(d.temp_day_c >= 27 for d in forecast_days)
        cold = any(d.temp_day_c <= 10 for d in forecast_days)
        wet  = any(d.precipitation_mm >= 2.0 for d in forecast_days)
        if hot: clothing.append("Hat & sunglasses; light fabrics")
        if cold: clothing.append("Warm layer / light jacket")
        if wet:  essentials.append("Compact umbrella / rain jacket")

    return {
        "essentials": essentials,
        "clothing": clothing,
        "toiletries": toiletries,
        "electronics": electronics,
    }


# (Optional) LLM polish if OPENAI_API_KEY available
def maybe_polish(text: str) -> str:
    if not settings.OPENAI_API_KEY or ChatOpenAI is None:
        return text
    try:
        llm = ChatOpenAI(model=settings.MODEL_NAME, temperature=settings.MODEL_TEMPERATURE)
        msg = llm.invoke([
            SystemMessage(content="Tighten and humanize wording. Keep details; remove fluff."),
            HumanMessage(content=text),
        ])
        return msg.content.strip()
    except Exception:
        return text  # never fail the request on polish


# =========================
# FastAPI
# =========================
app = FastAPI(title="Trip Planner (Free-API Edition)", version="2.0.0")

@app.post("/plan-trip", response_model=TripResponse)
async def plan_trip(req: TripRequest):
    destination = req.destination.strip()
    days = req.days
    today = datetime.utcnow().date()
    dates = [(today + timedelta(days=i)).isoformat() for i in range(days)]

    async with httpx.AsyncClient() as client:
        # 1) Geocode (Open-Meteo, free)
        geo = await geocode(client, destination)
        label = f"{geo['name']}, {geo['country']}"
        lat, lon, tz = geo["lat"], geo["lon"], geo["timezone"]

        # 2) Parallel fetch: forecast, POIs, events (Ticketmaster optional)
        start_dt = datetime.utcnow()
        end_dt = start_dt + timedelta(days=days+1)
        fc_task = asyncio.create_task(forecast(client, lat, lon, days, tz))
        poi_task = asyncio.create_task(wiki_pois(client, lat, lon))
        evt_task = asyncio.create_task(ticketmaster_events(client, lat, lon, start_dt, end_dt))
        forecast_days, pois, events = await asyncio.gather(fc_task, poi_task, evt_task)

    # 3) Build itinerary blocks
    daily: List[DayPlan] = []
    for i, d in enumerate(dates):
        daily.append(plan_blocks(i, d, [p.model_dump() for p in pois], [e for e in events]))

    # 4) Summary + packing
    summary_raw = summarize_context(label, forecast_days, pois, events)
    summary = maybe_polish(summary_raw)
    packing = build_packing_list(forecast_days)

    # 5) Shape response
    return TripResponse(
        destination=label,
        days=days,
        summary=summary,
        daily_itinerary=[
            DayPlan(
                day=dp.day,
                date=dp.date,
                morning=maybe_polish(dp.morning),
                afternoon=maybe_polish(dp.afternoon),
                evening=maybe_polish(dp.evening),
                meals=[maybe_polish(m) for m in dp.meals],
            )
            for dp in daily
        ],
        packing_list=packing,
        context={
            "geo": geo,
            "forecast": [fd.model_dump() for fd in forecast_days],
            "pois": [p.model_dump() for p in pois],
            "events": [e.model_dump() for e in events],
        },
    )
