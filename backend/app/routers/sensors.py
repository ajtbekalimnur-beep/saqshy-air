"""Sensors and real-time air quality telemetry router."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import Measurement, Room, Sensor
from app.schemas import CurrentRoomReading, MeasurementCreate, MeasurementResponse, SensorResponse, SensorStatusResponse
from app.services.recommendations import sync_recommendations_and_alerts_to_db
from app.services.simulator import calculate_aqi, generate_history, generate_reading

router = APIRouter(prefix="/api/sensors", tags=["Sensors"])


@router.get("/", response_model=List[SensorResponse])
def list_sensors(db: Session = Depends(get_db)):
    """List all registered environmental sensors with their statuses."""
    sensors = db.query(Sensor).all()
    return sensors


@router.get("/status", response_model=List[SensorStatusResponse])
def get_sensor_statuses(db: Session = Depends(get_db)):
    """Get connectivity, ping, and battery health status for all sensors."""
    sensors = db.query(Sensor).all()
    results = []
    now = datetime.utcnow()

    for s in sensors:
        room_name = s.room.name if s.room else "Unassigned"
        # Determine status dynamically if last seen > 10 mins ago
        sensor_status = s.status
        if s.last_seen and (now - s.last_seen) > timedelta(minutes=15) and not s.is_simulated:
            sensor_status = "offline"

        results.append(
            SensorStatusResponse(
                id=s.id,
                name=s.name,
                room_id=s.room_id,
                room_name=room_name,
                type=s.type,
                status=sensor_status,
                battery_level=s.battery_level,
                last_seen=s.last_seen or now,
                is_simulated=s.is_simulated,
                ping_ms=12 if sensor_status == "online" else 0,
            )
        )
    return results


@router.get("/current", response_model=List[CurrentRoomReading])
def get_current_readings(db: Session = Depends(get_db)):
    """Retrieve current environmental telemetry for all monitored rooms.

    Uses live database measurements if fresh, or generates realistic simulated
    telemetry if no recent data exists.
    """
    rooms = db.query(Room).all()
    current_readings: List[CurrentRoomReading] = []
    now = datetime.utcnow()

    for room in rooms:
        latest = (
            db.query(Measurement)
            .filter(Measurement.room_id == room.id)
            .order_by(desc(Measurement.timestamp))
            .first()
        )

        # If data is recent (within 10 minutes), use it
        if latest and (now - latest.timestamp) < timedelta(minutes=10):
            aqi, aqi_status = calculate_aqi(latest.pm25)
            current_readings.append(
                CurrentRoomReading(
                    room_id=room.id,
                    room_name=room.name,
                    room_type=room.type,
                    pm25=latest.pm25,
                    co2=latest.co2,
                    temperature=latest.temperature,
                    humidity=latest.humidity,
                    tvoc=latest.tvoc,
                    co=latest.co,
                    aqi=aqi,
                    aqi_status=aqi_status,
                    timestamp=latest.timestamp,
                    sensor_status="online",
                )
            )
        else:
            # Generate simulated reading for the room
            sim = generate_reading(scenario="normal", step=0, room_id=room.id)
            current_readings.append(
                CurrentRoomReading(
                    room_id=room.id,
                    room_name=room.name,
                    room_type=room.type,
                    pm25=sim["pm25"],
                    co2=sim["co2"],
                    temperature=sim["temperature"],
                    humidity=sim["humidity"],
                    tvoc=sim["tvoc"],
                    co=sim["co"],
                    aqi=sim["aqi"],
                    aqi_status=sim["aqi_status"],
                    timestamp=sim["timestamp"],
                    sensor_status="online (simulated)",
                )
            )

    return current_readings


@router.get("/history", response_model=List[MeasurementResponse])
def get_sensor_history(
    hours: int = Query(24, ge=1, le=168, description="History span in hours (1-168)"),
    room_id: Optional[int] = Query(None, description="Filter by room ID"),
    db: Session = Depends(get_db),
):
    """Retrieve historical air quality time series measurements for charts.

    Returns DB measurements, or synthesizes high-fidelity history if DB is sparse.
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    query = db.query(Measurement).filter(Measurement.timestamp >= since)
    if room_id is not None:
        query = query.filter(Measurement.room_id == room_id)

    records = query.order_by(Measurement.timestamp.asc()).all()

    # If DB has plenty of points, return them
    if len(records) >= 8:
        return records

    # Otherwise synthesize realistic history
    effective_room_id = room_id if room_id is not None else 1
    simulated_history = generate_history(
        hours=hours,
        scenario="normal",
        room_id=effective_room_id,
        interval_minutes=30 if hours <= 24 else 60,
    )

    response_items = []
    for idx, item in enumerate(simulated_history):
        response_items.append(
            MeasurementResponse(
                id=100000 + idx,
                sensor_id=item["sensor_id"],
                room_id=item["room_id"],
                pm25=item["pm25"],
                co2=item["co2"],
                temperature=item["temperature"],
                humidity=item["humidity"],
                tvoc=item["tvoc"],
                co=item["co"],
                timestamp=item["timestamp"],
                is_simulated=True,
                scenario=item["scenario"],
            )
        )
    return response_items


@router.post("/reading", response_model=MeasurementResponse, status_code=status.HTTP_201_CREATED)
def ingest_reading(
    reading_in: MeasurementCreate,
    db: Session = Depends(get_db),
):
    """Ingest real-time IoT sensor telemetry, update sensor status, and trigger safety evaluation."""
    room = db.query(Room).filter(Room.id == reading_in.room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with id {reading_in.room_id} not found",
        )

    now = reading_in.timestamp or datetime.utcnow()

    # Update sensor last seen if sensor_id is supplied
    if reading_in.sensor_id:
        sensor = db.query(Sensor).filter(Sensor.id == reading_in.sensor_id).first()
        if sensor:
            sensor.last_seen = now
            sensor.status = "online"

    db_measurement = Measurement(
        sensor_id=reading_in.sensor_id,
        room_id=reading_in.room_id,
        pm25=reading_in.pm25,
        co2=reading_in.co2,
        temperature=reading_in.temperature,
        humidity=reading_in.humidity,
        tvoc=reading_in.tvoc,
        co=reading_in.co,
        timestamp=now,
        is_simulated=reading_in.is_simulated,
        scenario=reading_in.scenario,
    )
    db.add(db_measurement)
    db.commit()
    db.refresh(db_measurement)

    # Trigger rule-based recommendation and alert check
    reading_dict = {
        "pm25": db_measurement.pm25,
        "co2": db_measurement.co2,
        "temperature": db_measurement.temperature,
        "humidity": db_measurement.humidity,
        "tvoc": db_measurement.tvoc,
        "co": db_measurement.co,
    }
    sync_recommendations_and_alerts_to_db(db, room.id, reading_dict)

    return db_measurement
