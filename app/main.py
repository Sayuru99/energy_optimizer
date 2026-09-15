from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import time
from app.core.config import get_settings
from app.db.session import engine, AsyncSessionLocal
from app.db.base import Base
from app.api.v1.api import api_router
from app.models.user import User
from app.models.factory import Factory
from app.models.machine import Machine
from app.models.tariff import Tariff
from app.models.report import Report
from app.core.security import get_password_hash

settings = get_settings()

async def seed_data(db: AsyncSession):
    from datetime import time, date, timedelta
    from app.models.optimization import OptimizationResult, OptimizationSummary
    from app.models.report import Report

    result = await db.execute(select(User).where(User.email == "manager@abcgarments.lk"))
    if result.scalar_one_or_none():
        return

    # 1. Factory
    factory = Factory(
        name="ABC Garments",
        code="ABC-KATUNAYAKE-01",
        tariff_plan="CEB Industrial Tariff I-2 / I-3",
        start_time=time(7, 0),
        end_time=time(21, 0),
        working_days=26
    )
    db.add(factory)
    await db.flush()

    # 2. User
    admin = User(
        name="Kavinda Wickramasinghe",
        email="manager@abcgarments.lk",
        hashed_password=get_password_hash("energy@2024"),
        phone="0771234567",
        is_superuser=True,
        factory_id=factory.id
    )
    db.add(admin)

    # 3. Machines
    machines_data = [
        {
            "name": "Fabric Cutter",
            "category": "Cutting",
            "quantity": 2,
            "power_kw": 4.0,
            "required_hours": 3.0,
            "available_start": time(8, 0),
            "available_end": time(18, 0),
            "priority": "High",
            "color": "blue",
            "start": time(8, 0),
            "end": time(11, 0),
            "energy": 24.0,
            "cost": 600.0,
            "saving": 240.0
        },
        {
            "name": "Sewing Machine Line",
            "category": "Sewing",
            "quantity": 10,
            "power_kw": 0.5,
            "required_hours": 8.0,
            "available_start": time(8, 0),
            "available_end": time(17, 0),
            "priority": "High",
            "color": "green",
            "start": time(8, 0),
            "end": time(16, 30),
            "energy": 40.0,
            "cost": 1000.0,
            "saving": 0.0
        },
        {
            "name": "Steam Ironing Station",
            "category": "Finishing",
            "quantity": 2,
            "power_kw": 3.0,
            "required_hours": 5.0,
            "available_start": time(8, 0),
            "available_end": time(18, 0),
            "priority": "Medium",
            "color": "amber",
            "start": time(10, 0),
            "end": time(15, 0),
            "energy": 30.0,
            "cost": 750.0,
            "saving": 240.0
        },
    ]

    machine_objects = []
    for m in machines_data:
        machine = Machine(
            factory_id=factory.id,
            name=m["name"],
            category=m["category"],
            quantity=m["quantity"],
            power_kw=m["power_kw"],
            required_hours=m["required_hours"],
            available_start=m["available_start"],
            available_end=m["available_end"],
            priority=m["priority"],
            color=m["color"]
        )
        db.add(machine)
        machine_objects.append((machine, m))

    await db.flush()

    # 4. Tariffs
    tariffs = [
        Tariff(period="Off-Peak", start_time=time(22, 30), end_time=time(5, 30), rate_per_kwh=15.0),
        Tariff(period="Day", start_time=time(5, 30), end_time=time(18, 30), rate_per_kwh=25.0),
        Tariff(period="Peak", start_time=time(18, 30), end_time=time(22, 30), rate_per_kwh=45.0),
    ]
    db.add_all(tariffs)

    # 5. Optimization Results + Summary
    current_cost = 2830.0
    optimized_cost = 2350.0
    daily_saving = 480.0
    monthly_saving = 12480.0
    saving_percentage = 16.97
    total_energy = 94.0

    for machine, m in machine_objects:
        db.add(OptimizationResult(
            factory_id=factory.id,
            machine_id=machine.id,
            scheduled_start=m["start"],
            scheduled_end=m["end"],
            energy_kwh=m["energy"],
            cost=m["cost"]
        ))

    db.add(OptimizationSummary(
        factory_id=factory.id,
        current_cost=current_cost,
        optimized_cost=optimized_cost,
        daily_saving=daily_saving,
        monthly_saving=monthly_saving,
        saving_percentage=saving_percentage
    ))

    # 6. Reports (last 7 days)
    today = date.today()
    report_data = [
        (0, 2830, 2350, 480, 94),
        (1, 2850, 2360, 490, 95),
        (2, 2810, 2340, 470, 93),
        (3, 2840, 2355, 485, 94),
        (4, 2860, 2370, 490, 95),
        (5, 2820, 2345, 475, 94),
        (6, 2830, 2350, 480, 94),
    ]

    for days_ago, curr, opt, sav, energy in report_data:
        db.add(Report(
            factory_id=factory.id,
            report_date=today - timedelta(days=days_ago),
            current_cost=curr,
            optimized_cost=opt,
            saving=sav,
            energy_kwh=energy,
            saving_percentage=round((sav / curr) * 100, 2)
        ))

    await db.commit()
    print("Seed data created successfully!")

    
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        await seed_data(db)
    yield
    await engine.dispose()

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": "Energy Optimization API is running"}