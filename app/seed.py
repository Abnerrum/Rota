from datetime import datetime, timedelta, timezone

from geoalchemy2.elements import WKTElement
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Customer, ServiceOrder, Technician, Vehicle


def point(lat: float, lng: float):
    return WKTElement(f"POINT({lng} {lat})", srid=4326)


def seed_database():
    db = SessionLocal()
    try:
        if db.scalar(select(Customer.id).limit(1)):
            return

        customers = [
            Customer(name="Loja Centro", address="Centro, Goiânia", lat=-16.6799, lng=-49.2550, location=point(-16.6799, -49.2550)),
            Customer(name="Cliente Bueno", address="Setor Bueno, Goiânia", lat=-16.7040, lng=-49.2730, location=point(-16.7040, -49.2730)),
            Customer(name="Empresa Aparecida", address="Aparecida de Goiânia", lat=-16.8235, lng=-49.2439, location=point(-16.8235, -49.2439)),
            Customer(name="Cliente Jardim América", address="Jardim América, Goiânia", lat=-16.7160, lng=-49.2910, location=point(-16.7160, -49.2910)),
        ]
        db.add_all(customers)
        db.flush()

        technicians = [
            Technician(name="Ana Silva", lat=-16.6869, lng=-49.2648, location=point(-16.6869, -49.2648), status="Disponível", capacity=4, skills=["instalacao", "manutencao"]),
            Technician(name="Carlos Souza", lat=-16.7270, lng=-49.2530, location=point(-16.7270, -49.2530), status="Em rota", capacity=3, skills=["manutencao"]),
            Technician(name="Marcos Lima", lat=-16.7490, lng=-49.2850, location=point(-16.7490, -49.2850), status="Disponível", capacity=4, skills=["instalacao", "vistoria"]),
        ]
        db.add_all(technicians)
        db.flush()

        vehicles = [
            Vehicle(plate="ROT1A01", model="Fiat Fiorino", status="Disponível", capacity_kg=650, technician_id=technicians[0].id),
            Vehicle(plate="ROT1A02", model="Renault Kangoo", status="Em rota", capacity_kg=700, technician_id=technicians[1].id),
        ]
        db.add_all(vehicles)
        db.flush()

        now = datetime.now(timezone.utc)
        orders = [
            ServiceOrder(customer_id=customers[0].id, address=customers[0].address, lat=customers[0].lat, lng=customers[0].lng, location=point(customers[0].lat, customers[0].lng), priority="Alta", status="Pendente", type="manutencao", sla_hours=4, created_at=now - timedelta(hours=3.2)),
            ServiceOrder(customer_id=customers[1].id, address=customers[1].address, lat=customers[1].lat, lng=customers[1].lng, location=point(customers[1].lat, customers[1].lng), priority="Normal", status="Pendente", type="instalacao", sla_hours=24, created_at=now - timedelta(hours=8)),
            ServiceOrder(customer_id=customers[2].id, address=customers[2].address, lat=customers[2].lat, lng=customers[2].lng, location=point(customers[2].lat, customers[2].lng), priority="Crítica", status="Pendente", type="manutencao", sla_hours=2, created_at=now - timedelta(hours=1.7)),
            ServiceOrder(customer_id=customers[3].id, address=customers[3].address, lat=customers[3].lat, lng=customers[3].lng, location=point(customers[3].lat, customers[3].lng), priority="Normal", status="Pendente", type="vistoria", sla_hours=12, created_at=now - timedelta(hours=10.5)),
        ]
        db.add_all(orders)
        db.commit()
    finally:
        db.close()
