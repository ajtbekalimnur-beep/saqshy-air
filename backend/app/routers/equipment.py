"""Equipment management and dynamic operational recommendation router."""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import Equipment, Measurement, Room
from app.schemas import EquipmentCreate, EquipmentResponse, EquipmentUpdate, EquipmentWithRecommendation

router = APIRouter(prefix="/api/equipment", tags=["Equipment"])


class EquipmentStatusUpdate(BaseModel):
    status: Optional[str] = None
    mode: Optional[str] = None


@router.get("/", response_model=List[EquipmentWithRecommendation])
def list_equipment(db: Session = Depends(get_db)):
    """List all smart air equipment paired with intelligent operational recommendations based on real-time room telemetry."""
    equipment_list = db.query(Equipment).all()
    results: List[EquipmentWithRecommendation] = []

    for eq in equipment_list:
        room = db.query(Room).filter(Room.id == eq.room_id).first()
        room_name = room.name if room else "Unknown Room"

        # Fetch latest reading in this equipment's room
        latest = (
            db.query(Measurement)
            .filter(Measurement.room_id == eq.room_id)
            .order_by(desc(Measurement.timestamp))
            .first()
        )

        pm25 = latest.pm25 if latest else 8.0
        co2 = latest.co2 if latest else 480.0
        humidity = latest.humidity if latest else 45.0

        rec_status = "idle"
        rec_mode = "auto"
        reason = "Operating within nominal efficiency limits."

        category = eq.category.lower()
        if "purifier" in category:
            if pm25 > 75.0:
                rec_status = "running"
                rec_mode = "turbo"
                reason = f"PM2.5 is high ({pm25:.1f} µg/m³). Turbo filtration recommended to scrub particles rapidly."
            elif pm25 > 35.0:
                rec_status = "running"
                rec_mode = "auto"
                reason = f"PM2.5 is elevated ({pm25:.1f} µg/m³). Active air purification advised."
            else:
                rec_status = "idle"
                rec_mode = "eco"
                reason = f"PM2.5 is pristine ({pm25:.1f} µg/m³). Eco mode recommended to save power."

        elif "humidifier" in category and "dehumidifier" not in category:
            if humidity < 35.0:
                rec_status = "running"
                rec_mode = "auto"
                reason = f"Relative humidity is low ({humidity:.1f}%). Humidification advised to reach 45% target."
            else:
                rec_status = "idle"
                rec_mode = "auto"
                reason = f"Relative humidity is balanced ({humidity:.1f}%)."

        elif "dehumidifier" in category:
            if humidity > 65.0:
                rec_status = "running"
                rec_mode = "auto"
                reason = f"Relative humidity is high ({humidity:.1f}%). Active dehumidification needed to prevent mold."
            else:
                rec_status = "idle"
                rec_mode = "auto"
                reason = f"Relative humidity is balanced ({humidity:.1f}%)."

        elif "ventilation" in category or "hrv" in category or "fan" in category:
            if co2 > 1200.0:
                rec_status = "running"
                rec_mode = "turbo"
                reason = f"CO2 concentration is high ({co2:.0f} ppm). High-speed fresh air exchange required."
            elif co2 > 900.0:
                rec_status = "running"
                rec_mode = "auto"
                reason = f"CO2 is moderately elevated ({co2:.0f} ppm). Continuous fresh air exchange recommended."
            else:
                rec_status = "running"
                rec_mode = "eco"
                reason = f"CO2 is fresh ({co2:.0f} ppm). Low-speed baseline ventilation adequate."

        results.append(
            EquipmentWithRecommendation(
                id=eq.id,
                room_id=eq.room_id,
                room_name=room_name,
                name=eq.name,
                category=eq.category,
                status=eq.status,
                mode=eq.mode,
                last_maintenance=eq.last_maintenance,
                recommended_status=rec_status,
                recommended_mode=rec_mode,
                reason=reason,
            )
        )

    return results


@router.post("/", response_model=EquipmentResponse, status_code=status.HTTP_201_CREATED)
def create_equipment(eq_in: EquipmentCreate, db: Session = Depends(get_db)):
    """Register new remediation or climate equipment."""
    room = db.query(Room).filter(Room.id == eq_in.room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with id {eq_in.room_id} not found",
        )

    eq = Equipment(
        room_id=eq_in.room_id,
        name=eq_in.name,
        category=eq_in.category,
        status=eq_in.status,
        mode=eq_in.mode,
        last_maintenance=datetime.utcnow(),
    )
    db.add(eq)
    db.commit()
    db.refresh(eq)
    return eq


@router.patch("/{id}/status", response_model=EquipmentResponse)
def update_equipment_status(
    id: int,
    status_in: EquipmentStatusUpdate,
    db: Session = Depends(get_db),
):
    """Toggle operational status (running, idle, off) or mode (auto, turbo, eco, manual)."""
    eq = db.query(Equipment).filter(Equipment.id == id).first()
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment with id {id} not found",
        )

    if status_in.status is not None:
        eq.status = status_in.status
    if status_in.mode is not None:
        eq.mode = status_in.mode

    db.commit()
    db.refresh(eq)
    return eq
