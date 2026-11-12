"""Interactive scenario simulation and demo controller router."""

from datetime import datetime
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Measurement, Room, Sensor
from app.schemas import DemoScenario, DemoStatusResponse
from app.services.recommendations import sync_recommendations_and_alerts_to_db
from app.services.simulator import (
    ALL_SCENARIOS,
    SCENARIO_NORMAL,
    SCENARIOS_CATALOG,
    generate_reading,
)

router = APIRouter(prefix="/api/demo", tags=["Demo Simulator"])


class DemoState:
    """In-memory active demo state holder."""
    def __init__(self):
        self.active_scenario: str = SCENARIO_NORMAL
        self.step: int = 0
        self.is_active: bool = False
        self.updated_at: datetime = datetime.utcnow()

    def start(self, scenario: str):
        self.active_scenario = scenario
        self.step = 0
        self.is_active = True
        self.updated_at = datetime.utcnow()

    def stop(self):
        self.active_scenario = SCENARIO_NORMAL
        self.step = 0
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def advance_step(self) -> int:
        self.step += 1
        self.updated_at = datetime.utcnow()
        return self.step


# Module-level singleton instance
demo_state = DemoState()


@router.get("/scenarios", response_model=List[DemoScenario])
def list_scenarios():
    """List all available indoor air quality demonstration scenarios with their baseline profiles."""
    scenarios_list: List[DemoScenario] = []
    for sc_id, meta in SCENARIOS_CATALOG.items():
        scenarios_list.append(
            DemoScenario(
                id=meta["id"],
                name=meta["name"],
                description=meta["description"],
                typical_readings=meta["typical_readings"],
            )
        )
    return scenarios_list


@router.post("/start/{scenario_id}", response_model=DemoStatusResponse)
def start_demo_scenario(scenario_id: str, db: Session = Depends(get_db)):
    """Activate an environmental scenario (e.g. cooking spike, smog infiltration, poor ventilation)."""
    clean_id = scenario_id.lower().strip()
    if clean_id not in SCENARIOS_CATALOG and clean_id not in ALL_SCENARIOS:
        valid_options = ", ".join(SCENARIOS_CATALOG.keys())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown scenario '{scenario_id}'. Valid options: {valid_options}",
        )

    demo_state.start(clean_id)

    # Immediately inject an initial step reading into the database
    first_room = db.query(Room).first()
    room_id = first_room.id if first_room else 1
    reading = generate_reading(scenario=clean_id, step=0, room_id=room_id)

    db_m = Measurement(
        room_id=room_id,
        pm25=reading["pm25"],
        co2=reading["co2"],
        temperature=reading["temperature"],
        humidity=reading["humidity"],
        tvoc=reading["tvoc"],
        co=reading["co"],
        timestamp=datetime.utcnow(),
        is_simulated=True,
        scenario=clean_id,
    )
    db.add(db_m)
    db.commit()

    sync_recommendations_and_alerts_to_db(db, room_id, reading)

    return DemoStatusResponse(
        active_scenario=demo_state.active_scenario,
        step=demo_state.step,
        is_active=demo_state.is_active,
        updated_at=demo_state.updated_at,
    )


@router.post("/stop", response_model=DemoStatusResponse)
def stop_demo_scenario():
    """Stop active demonstration scenario and return simulator to healthy baseline."""
    demo_state.stop()
    return DemoStatusResponse(
        active_scenario=demo_state.active_scenario,
        step=demo_state.step,
        is_active=demo_state.is_active,
        updated_at=demo_state.updated_at,
    )


@router.get("/status", response_model=DemoStatusResponse)
def get_demo_status():
    """Get status of the currently active demo scenario and step counter."""
    return DemoStatusResponse(
        active_scenario=demo_state.active_scenario,
        step=demo_state.step,
        is_active=demo_state.is_active,
        updated_at=demo_state.updated_at,
    )


@router.get("/readings")
def get_demo_readings(advance: bool = True, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retrieve current readings for the active demo scenario with optional step advancement."""
    if advance and demo_state.is_active:
        step = demo_state.advance_step()
    else:
        step = demo_state.step

    # Find target room (e.g. Kitchen for cooking, Living Room otherwise)
    target_room = None
    if demo_state.active_scenario == "cooking":
        target_room = db.query(Room).filter(Room.type == "kitchen").first()

    if not target_room:
        target_room = db.query(Room).first()

    room_id = target_room.id if target_room else 1
    room_name = target_room.name if target_room else "Living Room"

    reading = generate_reading(
        scenario=demo_state.active_scenario,
        step=step,
        room_id=room_id,
    )

    # Persist measurement to database so all sensor charts update
    db_m = Measurement(
        room_id=room_id,
        pm25=reading["pm25"],
        co2=reading["co2"],
        temperature=reading["temperature"],
        humidity=reading["humidity"],
        tvoc=reading["tvoc"],
        co=reading["co"],
        timestamp=datetime.utcnow(),
        is_simulated=True,
        scenario=demo_state.active_scenario,
    )
    db.add(db_m)
    db.commit()

    sync_recommendations_and_alerts_to_db(db, room_id, reading)

    return {
        "scenario": demo_state.active_scenario,
        "step": step,
        "is_active": demo_state.is_active,
        "room_id": room_id,
        "room_name": room_name,
        "reading": reading,
    }
