from __future__ import annotations

import os
from typing import TypedDict, Optional

from fastapi import FastAPI
from typing_extensions import Annotated
from pydantic import BaseModel, Field, StringConstraints




# LangChain / LangGraph
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

# ---------- Agent Memory (State) ----------
class TripState(TypedDict):
    destination: str
    days: int
    itinerary: str
    packing_list: str

# ---------- Simple fallback (no API key) ----------
def _fallback_itinerary(destination: str, days: int) -> str:
    lines = [f"Trip to {destination} — {days} day(s) itinerary:"]
    for d in range(1, days + 1):
        lines.append(
            f"Day {d}: Morning—City walk; Afternoon—Top landmark; Evening—Local food crawl."
        )
    return "\n".join(lines)

def _fallback_packing_list(destination: str, itinerary: str) -> str:
    return (
        "Essentials: Passport/ID, wallet, phone, charger, meds.\n"
        "Clothing: 3–5 outfits, comfy walking shoes, light jacket.\n"
        "Toiletries: toothbrush, toothpaste, sunscreen, deodorant.\n"
        f"Destination-specific for {destination}: small umbrella, reusable water bottle."
    )

def _has_openai_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))

def _make_llm(model: str = "gpt-4o-mini", temperature: float = 0.3) -> Optional[ChatOpenAI]:
    if not _has_openai_key():
        return None
    return ChatOpenAI(model=model, temperature=temperature)

# ---------- Nodes (Skills) ----------
def create_itinerary(state: TripState) -> TripState:
    destination = state["destination"]
    days = state["days"]

    llm = _make_llm()
    if llm is None:
        state["itinerary"] = _fallback_itinerary(destination, days)
        return state

    system = SystemMessage(
        content=(
            "You are a practical travel planner. Write concise, specific day-by-day plans "
            "with morning/afternoon/evening blocks and 1–2 food ideas per day. Avoid fluff."
        )
    )
    user = HumanMessage(
        content=f"Create a {days}-day travel itinerary for a trip to {destination}. "
                f"Keep it actionable and walkable where possible."
    )
    resp = llm.invoke([system, user])
    state["itinerary"] = resp.content.strip()
    return state

def suggest_packing_list(state: TripState) -> TripState:
    destination = state["destination"]
    itinerary = state["itinerary"]

    llm = _make_llm()
    if llm is None:
        state["packing_list"] = _fallback_packing_list(destination, itinerary)
        return state

    system = SystemMessage(
        content=(
            "You prepare packing lists tailored to an itinerary. Group items under: "
            "Essentials, Clothing, Toiletries, Electronics, Destination-specific. Be concise."
        )
    )
    user = HumanMessage(
        content=f"Based on this itinerary for {destination}, suggest a packing list:\n\n{itinerary}"
    )
    resp = llm.invoke([system, user])
    state["packing_list"] = resp.content.strip()
    return state

# ---------- Build the Workflow (Graph) ----------
def build_compiled_graph():
    graph = StateGraph(TripState)
    graph.add_node("create_itinerary", create_itinerary)
    graph.add_node("suggest_packing_list", suggest_packing_list)

    graph.set_entry_point("create_itinerary")
    graph.add_edge("create_itinerary", "suggest_packing_list")
    graph.add_edge("suggest_packing_list", END)

    return graph.compile()

compiled_app = build_compiled_graph()

# ---------- FastAPI ----------
app = FastAPI(
    title="AI Travel Planner API",
    version="1.0.0",
    description="Send a destination and days; get an itinerary and packing list."
)

class TripRequest(BaseModel):
    destination: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=2)
    ] = Field(..., example="Tokyo")

    days: Annotated[
        int,
        Field(ge=1, le=30, example=5)
    ]

class TripResponse(BaseModel):
    destination: str
    days: int
    itinerary: str
    packing_list: str

@app.post("/plan-trip", response_model=TripResponse)
def plan_trip(req: TripRequest):
    # Initial state
    init_state: TripState = {
        "destination": req.destination,
        "days": req.days,
        "itinerary": "",
        "packing_list": "",
    }
    final_state: TripState = compiled_app.invoke(init_state)
    return TripResponse(
        destination=final_state["destination"],
        days=final_state["days"],
        itinerary=final_state["itinerary"],
        packing_list=final_state["packing_list"],
    )
