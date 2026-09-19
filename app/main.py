from contextlib import asynccontextmanager
from datetime import datetime, timezone
from math import atan2, cos, radians, sin, sqrt
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.cobli import CobliClient, CobliError
from app.database import Base, engine, get_db
from app.models import Customer, ServiceOrder, Technician, Vehicle
from app.schemas import (
    CustomerCreate, CustomerOut, CustomerUpdate,
    OrderCreate, OrderUpdate,
    TechnicianCreate, TechnicianOut, TechnicianUpdate,
    VehicleCreate, VehicleOut, VehicleUpdate,
)
from app.seed import seed_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield


app = FastAPI(
    title="Rota API",
    version="0.4.0",
    description="Plataforma brasileira para operações de campo, rotas e ordens de serviço.",
    lifespan=lifespan,
)

PRIORITY_WEIGHT = {"Crítica": 3, "Alta": 2, "Normal": 1}


def point(lat: float, lng: float):
    return WKTElement(f"POINT({lng} {lat})", srid=4326)


def distance(a, b):
    radius = 6371
    p1, p2 = radians(a["lat"]), radians(b["lat"])
    dp = radians(b["lat"] - a["lat"])
    dl = radians(b["lng"] - a["lng"])
    x = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * radius * atan2(sqrt(x), sqrt(1 - x))


def age_hours(order: ServiceOrder):
    created = order.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return max((datetime.now(timezone.utc) - created).total_seconds() / 3600, 0)


def sla_risk(order: ServiceOrder):
    ratio = age_hours(order) / max(order.sla_hours, 0.1)
    if ratio >= 1:
        return "Estourado"
    if ratio >= 0.75:
        return "Crítico"
    if ratio >= 0.5:
        return "Atenção"
    return "Dentro do prazo"


def order_dict(order: ServiceOrder):
    age = age_hours(order)
    return {
        "id": order.id,
        "customer_id": order.customer_id,
        "customer": order.customer.name if order.customer else f"Cliente #{order.customer_id}",
        "technician_id": order.technician_id,
        "vehicle_id": order.vehicle_id,
        "address": order.address,
        "lat": order.lat,
        "lng": order.lng,
        "priority": order.priority,
        "status": order.status,
        "type": order.type,
        "sla_hours": order.sla_hours,
        "age_hours": round(age, 1),
        "sla_risk": sla_risk(order),
        "sla_remaining_hours": round(order.sla_hours - age, 1),
        "created_at": order.created_at,
    }


def update_instance(instance, payload: dict):
    lat_changed = "lat" in payload
    lng_changed = "lng" in payload
    for key, value in payload.items():
        setattr(instance, key, value)
    if hasattr(instance, "location") and (lat_changed or lng_changed):
        instance.location = point(instance.lat, instance.lng)


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {
        "status": "ok",
        "database": "online",
        "service": "rota-api",
        "version": app.version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    orders = db.scalars(select(ServiceOrder).options(joinedload(ServiceOrder.customer))).all()
    techs = db.scalars(select(Technician)).all()
    return {
        "orders": len(orders),
        "technicians": len(techs),
        "pending": sum(o.status == "Pendente" for o in orders),
        "available_technicians": sum(t.status == "Disponível" for t in techs),
        "critical_orders": sum(o.priority == "Crítica" for o in orders),
        "sla_risk": sum(sla_risk(o) in {"Crítico", "Estourado"} for o in orders),
        "routes": sum(o.technician_id is not None for o in orders),
    }


# CLIENTES
@app.get("/api/customers", response_model=list[CustomerOut])
def list_customers(db: Session = Depends(get_db)):
    return db.scalars(select(Customer).order_by(Customer.name)).all()


@app.post("/api/customers", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(data: CustomerCreate, db: Session = Depends(get_db)):
    obj = Customer(**data.model_dump(), location=point(data.lat, data.lng))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@app.get("/api/customers/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    obj = db.get(Customer, customer_id)
    if not obj:
        raise HTTPException(404, "Cliente não encontrado.")
    return obj


@app.patch("/api/customers/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, data: CustomerUpdate, db: Session = Depends(get_db)):
    obj = db.get(Customer, customer_id)
    if not obj:
        raise HTTPException(404, "Cliente não encontrado.")
    update_instance(obj, data.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(obj)
    return obj


@app.delete("/api/customers/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    obj = db.get(Customer, customer_id)
    if not obj:
        raise HTTPException(404, "Cliente não encontrado.")
    if db.scalar(select(func.count(ServiceOrder.id)).where(ServiceOrder.customer_id == customer_id)):
        raise HTTPException(409, "Cliente possui ordens de serviço e não pode ser excluído.")
    db.delete(obj)
    db.commit()


# TÉCNICOS
@app.get("/api/technicians", response_model=list[TechnicianOut])
def list_technicians(status_filter: str | None = Query(default=None, alias="status"), db: Session = Depends(get_db)):
    stmt = select(Technician).order_by(Technician.name)
    if status_filter:
        stmt = stmt.where(func.lower(Technician.status) == status_filter.lower())
    return db.scalars(stmt).all()


@app.post("/api/technicians", response_model=TechnicianOut, status_code=status.HTTP_201_CREATED)
def create_technician(data: TechnicianCreate, db: Session = Depends(get_db)):
    obj = Technician(**data.model_dump(), location=point(data.lat, data.lng))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@app.get("/api/technicians/{technician_id}", response_model=TechnicianOut)
def get_technician(technician_id: int, db: Session = Depends(get_db)):
    obj = db.get(Technician, technician_id)
    if not obj:
        raise HTTPException(404, "Técnico não encontrado.")
    return obj


@app.patch("/api/technicians/{technician_id}", response_model=TechnicianOut)
def update_technician(technician_id: int, data: TechnicianUpdate, db: Session = Depends(get_db)):
    obj = db.get(Technician, technician_id)
    if not obj:
        raise HTTPException(404, "Técnico não encontrado.")
    update_instance(obj, data.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(obj)
    return obj


@app.delete("/api/technicians/{technician_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_technician(technician_id: int, db: Session = Depends(get_db)):
    obj = db.get(Technician, technician_id)
    if not obj:
        raise HTTPException(404, "Técnico não encontrado.")
    for order in obj.orders:
        order.technician_id = None
    for vehicle in obj.vehicles:
        vehicle.technician_id = None
    db.delete(obj)
    db.commit()


# VEÍCULOS
@app.get("/api/vehicles", response_model=list[VehicleOut])
def list_vehicles(db: Session = Depends(get_db)):
    return db.scalars(select(Vehicle).order_by(Vehicle.plate)).all()


@app.post("/api/vehicles", response_model=VehicleOut, status_code=status.HTTP_201_CREATED)
def create_vehicle(data: VehicleCreate, db: Session = Depends(get_db)):
    if data.technician_id and not db.get(Technician, data.technician_id):
        raise HTTPException(400, "Técnico informado não existe.")
    obj = Vehicle(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@app.get("/api/vehicles/{vehicle_id}", response_model=VehicleOut)
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    obj = db.get(Vehicle, vehicle_id)
    if not obj:
        raise HTTPException(404, "Veículo não encontrado.")
    return obj


@app.patch("/api/vehicles/{vehicle_id}", response_model=VehicleOut)
def update_vehicle(vehicle_id: int, data: VehicleUpdate, db: Session = Depends(get_db)):
    obj = db.get(Vehicle, vehicle_id)
    if not obj:
        raise HTTPException(404, "Veículo não encontrado.")
    payload = data.model_dump(exclude_unset=True)
    if payload.get("technician_id") and not db.get(Technician, payload["technician_id"]):
        raise HTTPException(400, "Técnico informado não existe.")
    update_instance(obj, payload)
    db.commit()
    db.refresh(obj)
    return obj


@app.delete("/api/vehicles/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    obj = db.get(Vehicle, vehicle_id)
    if not obj:
        raise HTTPException(404, "Veículo não encontrado.")
    db.delete(obj)
    db.commit()


# ORDENS DE SERVIÇO
@app.get("/api/orders")
def list_orders(
    priority: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    risk: str | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(ServiceOrder).options(joinedload(ServiceOrder.customer)).order_by(ServiceOrder.created_at.desc())
    if priority:
        stmt = stmt.where(func.lower(ServiceOrder.priority) == priority.lower())
    if status_filter:
        stmt = stmt.where(func.lower(ServiceOrder.status) == status_filter.lower())
    result = [order_dict(o) for o in db.scalars(stmt).all()]
    if risk:
        result = [o for o in result if o["sla_risk"].lower() == risk.lower()]
    return result


@app.post("/api/orders", status_code=status.HTTP_201_CREATED)
def create_order(data: OrderCreate, db: Session = Depends(get_db)):
    if not db.get(Customer, data.customer_id):
        raise HTTPException(400, "Cliente informado não existe.")
    if data.technician_id and not db.get(Technician, data.technician_id):
        raise HTTPException(400, "Técnico informado não existe.")
    if data.vehicle_id and not db.get(Vehicle, data.vehicle_id):
        raise HTTPException(400, "Veículo informado não existe.")
    obj = ServiceOrder(**data.model_dump(), location=point(data.lat, data.lng))
    db.add(obj)
    db.commit()
    obj = db.scalar(select(ServiceOrder).options(joinedload(ServiceOrder.customer)).where(ServiceOrder.id == obj.id))
    return order_dict(obj)


@app.get("/api/orders/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db)):
    obj = db.scalar(select(ServiceOrder).options(joinedload(ServiceOrder.customer)).where(ServiceOrder.id == order_id))
    if not obj:
        raise HTTPException(404, "Ordem de serviço não encontrada.")
    return order_dict(obj)


@app.patch("/api/orders/{order_id}")
def update_order(order_id: int, data: OrderUpdate, db: Session = Depends(get_db)):
    obj = db.get(ServiceOrder, order_id)
    if not obj:
        raise HTTPException(404, "Ordem de serviço não encontrada.")
    payload = data.model_dump(exclude_unset=True)
    if payload.get("customer_id") and not db.get(Customer, payload["customer_id"]):
        raise HTTPException(400, "Cliente informado não existe.")
    if payload.get("technician_id") and not db.get(Technician, payload["technician_id"]):
        raise HTTPException(400, "Técnico informado não existe.")
    if payload.get("vehicle_id") and not db.get(Vehicle, payload["vehicle_id"]):
        raise HTTPException(400, "Veículo informado não existe.")
    update_instance(obj, payload)
    db.commit()
    obj = db.scalar(select(ServiceOrder).options(joinedload(ServiceOrder.customer)).where(ServiceOrder.id == order_id))
    return order_dict(obj)


@app.delete("/api/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    obj = db.get(ServiceOrder, order_id)
    if not obj:
        raise HTTPException(404, "Ordem de serviço não encontrada.")
    db.delete(obj)
    db.commit()


@app.post("/api/optimize")
def optimize(strategy: Literal["balanced", "nearest"] = "balanced", db: Session = Depends(get_db)):
    order_rows = db.scalars(
        select(ServiceOrder)
        .options(joinedload(ServiceOrder.customer))
        .where(ServiceOrder.status == "Pendente")
    ).all()
    technicians = db.scalars(select(Technician)).all()

    if not technicians:
        raise HTTPException(409, "Cadastre ao menos um técnico antes de otimizar.")

    pending_orders = sorted(
        order_rows,
        key=lambda o: (-PRIORITY_WEIGHT.get(o.priority, 0), o.sla_hours - age_hours(o)),
    )
    load = {t.id: 0 for t in technicians}
    result = []

    for order in pending_orders:
        compatible = [t for t in technicians if order.type in (t.skills or [])]
        candidates = compatible or technicians
        order_location = {"lat": order.lat, "lng": order.lng}

        def score(tech):
            tech_location = {"lat": tech.lat, "lng": tech.lng}
            km = distance(tech_location, order_location)
            if strategy == "nearest":
                return km
            capacity = max(tech.capacity, 1)
            load_penalty = (load[tech.id] / capacity) * 15
            status_penalty = 5 if tech.status != "Disponível" else 0
            return km + load_penalty + status_penalty

        tech = min(candidates, key=score)
        load[tech.id] += 1
        order.technician_id = tech.id

        result.append({
            "order": order_dict(order),
            "technician": {
                "id": tech.id, "name": tech.name, "lat": tech.lat, "lng": tech.lng,
                "status": tech.status, "capacity": tech.capacity, "skills": tech.skills,
            },
            "distance_km": round(distance({"lat": tech.lat, "lng": tech.lng}, order_location), 1),
            "assigned_load": load[tech.id],
            "strategy": strategy,
        })

    db.commit()
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
