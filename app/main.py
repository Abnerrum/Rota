from datetime import datetime, timezone
from math import atan2, cos, radians, sin, sqrt
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.cobli import CobliClient, CobliError

app = FastAPI(
    title="Rota API",
    version="0.3.0",
    description="Plataforma brasileira para operações de campo, rotas e ordens de serviço.",
)

technicians = [
    {"id": 1, "name": "Ana Silva", "lat": -16.6869, "lng": -49.2648, "status": "Disponível", "skills": ["instalacao", "manutencao"], "capacity": 4},
    {"id": 2, "name": "Carlos Souza", "lat": -16.7270, "lng": -49.2530, "status": "Em rota", "skills": ["manutencao"], "capacity": 3},
    {"id": 3, "name": "Marcos Lima", "lat": -16.7490, "lng": -49.2850, "status": "Disponível", "skills": ["instalacao", "vistoria"], "capacity": 4},
]

orders = [
    {"id": 1001, "customer": "Loja Centro", "address": "Centro, Goiânia", "lat": -16.6799, "lng": -49.2550, "priority": "Alta", "status": "Pendente", "type": "manutencao", "sla_hours": 4, "age_hours": 3.2},
    {"id": 1002, "customer": "Cliente Bueno", "address": "Setor Bueno, Goiânia", "lat": -16.7040, "lng": -49.2730, "priority": "Normal", "status": "Pendente", "type": "instalacao", "sla_hours": 24, "age_hours": 8.0},
    {"id": 1003, "customer": "Empresa Aparecida", "address": "Aparecida de Goiânia", "lat": -16.8235, "lng": -49.2439, "priority": "Crítica", "status": "Pendente", "type": "manutencao", "sla_hours": 2, "age_hours": 1.7},
    {"id": 1004, "customer": "Cliente Jardim América", "address": "Jardim América, Goiânia", "lat": -16.7160, "lng": -49.2910, "priority": "Normal", "status": "Pendente", "type": "vistoria", "sla_hours": 12, "age_hours": 10.5},
]

PRIORITY_WEIGHT = {"Crítica": 3, "Alta": 2, "Normal": 1}


def distance(a, b):
    radius = 6371
    p1, p2 = radians(a["lat"]), radians(b["lat"])
    dp = radians(b["lat"] - a["lat"])
    dl = radians(b["lng"] - a["lng"])
    x = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * radius * atan2(sqrt(x), sqrt(1 - x))


def sla_risk(order):
    ratio = order["age_hours"] / max(order["sla_hours"], 0.1)
    if ratio >= 1:
        return "Estourado"
    if ratio >= 0.75:
        return "Crítico"
    if ratio >= 0.5:
        return "Atenção"
    return "Dentro do prazo"


def enrich_order(order):
    item = dict(order)
    item["sla_risk"] = sla_risk(order)
    item["sla_remaining_hours"] = round(order["sla_hours"] - order["age_hours"], 1)
    return item


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "rota-api",
        "version": app.version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/dashboard")
def dashboard():
    enriched = [enrich_order(o) for o in orders]
    return {
        "orders": len(orders),
        "technicians": len(technicians),
        "pending": sum(o["status"] == "Pendente" for o in orders),
        "available_technicians": sum(t["status"] == "Disponível" for t in technicians),
        "critical_orders": sum(o["priority"] == "Crítica" for o in orders),
        "sla_risk": sum(o["sla_risk"] in {"Crítico", "Estourado"} for o in enriched),
        "routes": 0,
    }


@app.get("/api/technicians")
def get_technicians(status: str | None = Query(default=None)):
    if not status:
        return technicians
    return [t for t in technicians if t["status"].lower() == status.lower()]


@app.get("/api/orders")
def get_orders(
    priority: str | None = Query(default=None),
    status: str | None = Query(default=None),
    risk: str | None = Query(default=None),
):
    result = [enrich_order(o) for o in orders]
    if priority:
        result = [o for o in result if o["priority"].lower() == priority.lower()]
    if status:
        result = [o for o in result if o["status"].lower() == status.lower()]
    if risk:
        result = [o for o in result if o["sla_risk"].lower() == risk.lower()]
    return result


@app.post("/api/optimize")
def optimize(strategy: Literal["balanced", "nearest"] = "balanced"):
    pending_orders = sorted(
        [o for o in orders if o["status"] == "Pendente"],
        key=lambda o: (-PRIORITY_WEIGHT.get(o["priority"], 0), o["sla_hours"] - o["age_hours"]),
    )
    load = {t["id"]: 0 for t in technicians}
    result = []

    for order in pending_orders:
        compatible = [t for t in technicians if order["type"] in t.get("skills", [])]
        candidates = compatible or technicians

        def score(tech):
            km = distance(tech, order)
            if strategy == "nearest":
                return km
            capacity = max(tech.get("capacity", 1), 1)
            load_penalty = (load[tech["id"]] / capacity) * 15
            status_penalty = 5 if tech["status"] != "Disponível" else 0
            return km + load_penalty + status_penalty

        tech = min(candidates, key=score)
        load[tech["id"]] += 1
        result.append(
            {
                "order": enrich_order(order),
                "technician": tech,
                "distance_km": round(distance(tech, order), 1),
                "assigned_load": load[tech["id"]],
                "strategy": strategy,
            }
        )

    total_km = round(sum(item["distance_km"] for item in result), 1)
    return {
        "routes": result,
        "summary": {
            "orders_assigned": len(result),
            "estimated_distance_km": total_km,
            "strategy": strategy,
            "workload": load,
        },
    }


def cobli_call(method, *args, **kwargs):
    try:
        return getattr(CobliClient(), method)(*args, **kwargs)
    except CobliError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@app.get("/api/cobli/status")
def cobli_status():
    return CobliClient().status()


@app.get("/api/cobli/drivers")
def cobli_drivers(limit: int = 200, page: int = 1):
    return cobli_call("drivers", limit, page)


@app.get("/api/cobli/devices")
def cobli_devices(limit: int = 200, page: int = 1):
    return cobli_call("devices", limit, page)


@app.get("/api/cobli/routes")
def cobli_routes(start_in_millis: int | None = None, end_in_millis: int | None = None):
    return cobli_call("routes", start_in_millis, end_in_millis)


@app.get("/api/cobli/paths")
def cobli_paths(startDate: str, endDate: str, limit: int = 200, page: int = 1):
    return cobli_call("paths", startDate, endDate, limit, page)


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def home():
    return FileResponse("static/index.html")
