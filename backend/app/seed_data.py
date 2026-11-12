"""Database seed data initializer for SAQSHY AIR."""

from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session

from app.models import Conversation, Equipment, Measurement, Message, Room, Sensor
from app.services.simulator import generate_history, generate_reading

logger = logging.getLogger("saqshy.seed")


def seed_database_if_empty(db: Session) -> bool:
    """Populate default rooms, sensors, smart equipment, and 7-day historical telemetry if database is uninitialized."""
    if db.query(Room).count() > 0:
        logger.info("Database already seeded. Skipping initial seeding.")
        return False

    logger.info("Initializing SAQSHY AIR database with demo rooms, sensors, equipment, and historical telemetry...")

    # 1. Create Default Rooms
    living_room = Room(name="Living Room", type="living_room", floor=1)
    bedroom = Room(name="Master Bedroom", type="bedroom", floor=2)
    kitchen = Room(name="Kitchen", type="kitchen", floor=1)
    children_room = Room(name="Children's Room", type="children_room", floor=2)

    db.add_all([living_room, bedroom, kitchen, children_room])
    db.commit()
    db.refresh(living_room)
    db.refresh(bedroom)
    db.refresh(kitchen)
    db.refresh(children_room)

    # 2. Create Sensors for each room
    s1 = Sensor(name="Living Room Sentinel Pro", type="multi_sensor", room_id=living_room.id, status="online", battery_level=98, is_simulated=True)
    s2 = Sensor(name="Master Bedroom Air Monitor", type="multi_sensor", room_id=bedroom.id, status="online", battery_level=92, is_simulated=True)
    s3 = Sensor(name="Kitchen Range Sniffer", type="multi_sensor", room_id=kitchen.id, status="online", battery_level=100, is_simulated=True)
    s4 = Sensor(name="Children's Room EcoGuard", type="multi_sensor", room_id=children_room.id, status="online", battery_level=95, is_simulated=True)

    db.add_all([s1, s2, s3, s4])
    db.commit()
    db.refresh(s1)
    db.refresh(s2)
    db.refresh(s3)
    db.refresh(s4)

    # 3. Create Smart Air Remediation Equipment
    eq1 = Equipment(name="Living Room HEPA Purifier Pro", category="purifier", room_id=living_room.id, status="running", mode="auto", last_maintenance=datetime.utcnow() - timedelta(days=20))
    eq2 = Equipment(name="Master Bedroom Ultrasonic Humidifier", category="humidifier", room_id=bedroom.id, status="running", mode="auto", last_maintenance=datetime.utcnow() - timedelta(days=12))
    eq3 = Equipment(name="Kitchen High-Velocity Extractor", category="purifier", room_id=kitchen.id, status="idle", mode="auto", last_maintenance=datetime.utcnow() - timedelta(days=5))
    eq4 = Equipment(name="Smart Whole-House HRV Ventilation", category="ventilation", room_id=living_room.id, status="running", mode="eco", last_maintenance=datetime.utcnow() - timedelta(days=45))
    eq5 = Equipment(name="Children's Room Air Guard Purifier", category="purifier", room_id=children_room.id, status="running", mode="eco", last_maintenance=datetime.utcnow() - timedelta(days=15))
    eq6 = Equipment(name="Smart Dehumidifier 50L", category="dehumidifier", room_id=living_room.id, status="idle", mode="auto", last_maintenance=datetime.utcnow() - timedelta(days=30))

    db.add_all([eq1, eq2, eq3, eq4, eq5, eq6])
    db.commit()

    # 4. Generate 7 Days of Historical Telemetry (one reading every 2 hours per room = 84 points per room)
    now = datetime.utcnow()
    measurements_to_add = []

    room_configs = [
        (living_room.id, s1.id, "normal"),
        (bedroom.id, s2.id, "normal"),
        (kitchen.id, s3.id, "cooking"),
        (children_room.id, s4.id, "normal"),
    ]

    for room_id, sensor_id, primary_scenario in room_configs:
        history_points = generate_history(
            hours=168,  # 7 days
            scenario=primary_scenario,
            room_id=room_id,
            sensor_id=sensor_id,
            interval_minutes=120,  # every 2 hours
        )
        for p in history_points:
            measurements_to_add.append(
                Measurement(
                    room_id=room_id,
                    sensor_id=sensor_id,
                    pm25=p["pm25"],
                    co2=p["co2"],
                    temperature=p["temperature"],
                    humidity=p["humidity"],
                    tvoc=p["tvoc"],
                    co=p["co"],
                    timestamp=p["timestamp"],
                    is_simulated=True,
                    scenario=p["scenario"],
                )
            )

    # Add a fresh current reading for each room right now
    for room_id, sensor_id, scenario in room_configs:
        curr = generate_reading(scenario="normal", step=0, room_id=room_id, sensor_id=sensor_id, timestamp=now)
        measurements_to_add.append(
            Measurement(
                room_id=room_id,
                sensor_id=sensor_id,
                pm25=curr["pm25"],
                co2=curr["co2"],
                temperature=curr["temperature"],
                humidity=curr["humidity"],
                tvoc=curr["tvoc"],
                co=curr["co"],
                timestamp=now,
                is_simulated=True,
                scenario=curr["scenario"],
            )
        )

    db.bulk_save_objects(measurements_to_add)
    db.commit()

    # 5. Seed Welcome Conversation
    welcome_conv = Conversation(
        title="Welcome & System Orientation",
        created_at=now - timedelta(hours=1),
    )
    db.add(welcome_conv)
    db.commit()
    db.refresh(welcome_conv)

    welcome_msg = Message(
        conversation_id=welcome_conv.id,
        role="assistant",
        content=(
            "Welcome to **SAQSHY AIR**! I am your indoor air quality and environmental health assistant.\n\n"
            "All sensors across your **Living Room, Master Bedroom, Kitchen, and Children's Room** are currently active and transmitting telemetry. "
            "You can ask me questions about your indoor air metrics, check equipment recommendations, or explore real-world scenarios in the Demo simulator."
        ),
        timestamp=now - timedelta(hours=1),
    )
    db.add(welcome_msg)
    db.commit()

    logger.info("SAQSHY AIR database seeding completed successfully.")
    return True
