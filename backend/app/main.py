"""SAQSHY AIR FastAPI Backend Application.

Main entry point containing application lifecycle configuration, CORS middleware,
background simulation loop, and API router registrations.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import text
import pathlib

from app.database import Base, SessionLocal, engine
from app.models import Measurement, Room, Sensor
from app.routers import ai, demo, equipment, reports, rooms, sensors
from app.routers.demo import demo_state
from app.seed_data import seed_database_if_empty
from app.services.recommendations import sync_recommendations_and_alerts_to_db
from app.services.simulator import generate_reading

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("saqshy.main")


async def periodic_simulation_worker():
    """Background task that runs every 30 seconds to generate live telemetry points and advance active demo scenarios."""
    logger.info("Starting SAQSHY AIR background simulation worker (30-second interval)...")
    try:
        while True:
            await asyncio.sleep(30)
            try:
                with SessionLocal() as db:
                    all_rooms = db.query(Room).all()
                    if not all_rooms:
                        continue

                    # If interactive demo is running, advance scenario step
                    if demo_state.is_active:
                        demo_state.advance_step()
                        active_sc = demo_state.active_scenario
                        step = demo_state.step

                        # Kitchen for cooking, first room otherwise
                        target_room = None
                        if active_sc == "cooking":
                            target_room = db.query(Room).filter(Room.type == "kitchen").first()
                        if not target_room:
                            target_room = all_rooms[0]

                        reading = generate_reading(
                            scenario=active_sc,
                            step=step,
                            room_id=target_room.id,
                        )
                        db_m = Measurement(
                            room_id=target_room.id,
                            pm25=reading["pm25"],
                            co2=reading["co2"],
                            temperature=reading["temperature"],
                            humidity=reading["humidity"],
                            tvoc=reading["tvoc"],
                            co=reading["co"],
                            timestamp=datetime.utcnow(),
                            is_simulated=True,
                            scenario=active_sc,
                        )
                        db.add(db_m)
                        sync_recommendations_and_alerts_to_db(db, target_room.id, reading)

                    # Also update baseline readings across other simulated rooms
                    for rm in all_rooms:
                        if demo_state.is_active and rm.id == (target_room.id if 'target_room' in locals() and target_room else None):
                            continue

                        reading = generate_reading(
                            scenario="normal",
                            step=0,
                            room_id=rm.id,
                        )
                        db_m = Measurement(
                            room_id=rm.id,
                            pm25=reading["pm25"],
                            co2=reading["co2"],
                            temperature=reading["temperature"],
                            humidity=reading["humidity"],
                            tvoc=reading["tvoc"],
                            co=reading["co"],
                            timestamp=datetime.utcnow(),
                            is_simulated=True,
                            scenario="normal",
                        )
                        db.add(db_m)

                    db.commit()
                    logger.debug("Simulated telemetry batch committed for all rooms.")

            except Exception as e:
                logger.error(f"Error in background simulation loop: {e}", exc_info=True)

    except asyncio.CancelledError:
        logger.info("Background simulation worker stopped gracefully.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle context manager: initialize database, run seeds, and manage background tasks."""
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)

    # Populate default seed data if DB is empty
    with SessionLocal() as db:
        seed_database_if_empty(db)

    # Launch background simulator worker
    bg_task = asyncio.create_task(periodic_simulation_worker())

    yield

    # Clean shutdown of background worker
    bg_task.cancel()
    try:
        await bg_task
    except asyncio.CancelledError:
        pass


# Create FastAPI application
app = FastAPI(
    title="SAQSHY AIR API",
    description="Intelligent Indoor Air Quality Monitoring, AI Consultation, and Equipment Automation Backend.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for frontend applications
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(sensors.router)
app.include_router(ai.router)
app.include_router(demo.router)
app.include_router(rooms.router)
app.include_router(equipment.router)
app.include_router(reports.router)


# Serve frontend static files — search in multiple locations (local dev & cloud deploy)
_base = pathlib.Path(__file__).parent.parent.parent
_frontend_dir = None
for _candidate in [_base / "frontend", _base.parent / "frontend", pathlib.Path("/app/frontend")]:
    if _candidate.exists():
        _frontend_dir = _candidate
        break

if _frontend_dir:
    app.mount("/app", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")


@app.get("/")
def root():
    """Root entrypoint: serve frontend if available, otherwise return API info."""
    if _frontend_dir:
        index = _frontend_dir / "index.html"
        if index.exists():
            return FileResponse(str(index))
    return {"message": "SAQSHY AIR API", "version": "1.0.0"}


@app.get("/api/health")
def health_check():
    """Service health check endpoint verifying database connectivity."""
    db_status = "connected"
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status,
        "active_scenario": demo_state.active_scenario,
        "is_demo_active": demo_state.is_active,
    }
