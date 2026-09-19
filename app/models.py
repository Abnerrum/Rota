from datetime import datetime, timezone

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(160), nullable=True)
    address: Mapped[str] = mapped_column(String(240))
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    location = mapped_column(Geometry("POINT", srid=4326, spatial_index=True))

    orders: Mapped[list["ServiceOrder"]] = relationship(back_populates="customer")


class Technician(Base):
    __tablename__ = "technicians"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(40), default="Disponível")
    capacity: Mapped[int] = mapped_column(Integer, default=4)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    location = mapped_column(Geometry("POINT", srid=4326, spatial_index=True))

    vehicles: Mapped[list["Vehicle"]] = relationship(back_populates="technician")
    orders: Mapped[list["ServiceOrder"]] = relationship(back_populates="technician")


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    plate: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    model: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(40), default="Disponível")
    capacity_kg: Mapped[float] = mapped_column(Float, default=0)
    technician_id: Mapped[int | None] = mapped_column(ForeignKey("technicians.id"), nullable=True)

    technician: Mapped[Technician | None] = relationship(back_populates="vehicles")
    orders: Mapped[list["ServiceOrder"]] = relationship(back_populates="vehicle")


class ServiceOrder(Base):
    __tablename__ = "service_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    technician_id: Mapped[int | None] = mapped_column(ForeignKey("technicians.id"), nullable=True, index=True)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    address: Mapped[str] = mapped_column(String(240))
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    location = mapped_column(Geometry("POINT", srid=4326, spatial_index=True))
    priority: Mapped[str] = mapped_column(String(20), default="Normal", index=True)
    status: Mapped[str] = mapped_column(String(30), default="Pendente", index=True)
    type: Mapped[str] = mapped_column(String(60), default="manutencao")
    sla_hours: Mapped[float] = mapped_column(Float, default=24)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    customer: Mapped[Customer] = relationship(back_populates="orders")
    technician: Mapped[Technician | None] = relationship(back_populates="orders")
    vehicle: Mapped[Vehicle | None] = relationship(back_populates="orders")
