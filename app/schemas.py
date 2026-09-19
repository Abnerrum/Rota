from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CustomerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str | None = None
    email: str | None = None
    address: str
    lat: float
    lng: float


class CustomerUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    lat: float | None = None
    lng: float | None = None


class TechnicianCreate(BaseModel):
    name: str
    status: str = "Disponível"
    capacity: int = Field(default=4, ge=1, le=50)
    skills: list[str] = []
    lat: float
    lng: float


class TechnicianUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    capacity: int | None = Field(default=None, ge=1, le=50)
    skills: list[str] | None = None
    lat: float | None = None
    lng: float | None = None


class VehicleCreate(BaseModel):
    plate: str
    model: str
    status: str = "Disponível"
    capacity_kg: float = Field(default=0, ge=0)
    technician_id: int | None = None


class VehicleUpdate(BaseModel):
    plate: str | None = None
    model: str | None = None
    status: str | None = None
    capacity_kg: float | None = Field(default=None, ge=0)
    technician_id: int | None = None


class OrderCreate(BaseModel):
    customer_id: int
    technician_id: int | None = None
    vehicle_id: int | None = None
    address: str
    lat: float
    lng: float
    priority: str = "Normal"
    status: str = "Pendente"
    type: str = "manutencao"
    sla_hours: float = Field(default=24, gt=0)


class OrderUpdate(BaseModel):
    customer_id: int | None = None
    technician_id: int | None = None
    vehicle_id: int | None = None
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
    priority: str | None = None
    status: str | None = None
    type: str | None = None
    sla_hours: float | None = Field(default=None, gt=0)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CustomerOut(ORMModel):
    id: int
    name: str
    phone: str | None
    email: str | None
    address: str
    lat: float
    lng: float


class TechnicianOut(ORMModel):
    id: int
    name: str
    status: str
    capacity: int
    skills: list[str]
    lat: float
    lng: float


class VehicleOut(ORMModel):
    id: int
    plate: str
    model: str
    status: str
    capacity_kg: float
    technician_id: int | None


class OrderOut(ORMModel):
    id: int
    customer_id: int
    technician_id: int | None
    vehicle_id: int | None
    address: str
    lat: float
    lng: float
    priority: str
    status: str
    type: str
    sla_hours: float
    created_at: datetime
