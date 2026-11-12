"""Environmental sensor simulation engine for SAQSHY AIR.

Provides realistic multi-parameter indoor air quality generation, scenario-driven
progressions, and time-series historical telemetry with natural random noise.
"""

from datetime import datetime, timedelta
import math
import random
from typing import Any, Dict, List, Optional

# Scenarios supported by the simulation engine
SCENARIO_NORMAL = "normal"
SCENARIO_COOKING = "cooking"
SCENARIO_OUTDOOR_POLLUTION = "outdoor_pollution"
SCENARIO_LOW_HUMIDITY = "low_humidity"
SCENARIO_POOR_VENTILATION = "poor_ventilation"
SCENARIO_IMPROVEMENT = "improvement"

ALL_SCENARIOS = [
    SCENARIO_NORMAL,
    SCENARIO_COOKING,
    SCENARIO_OUTDOOR_POLLUTION,
    SCENARIO_LOW_HUMIDITY,
    SCENARIO_POOR_VENTILATION,
    SCENARIO_IMPROVEMENT,
]

SCENARIOS_CATALOG: Dict[str, Dict[str, Any]] = {
    SCENARIO_NORMAL: {
        "id": SCENARIO_NORMAL,
        "name": "Normal Healthy Baseline",
        "description": "Optimal indoor climate with clean air, low PM2.5 (5 µg/m³), fresh CO2 (450 ppm), and comfortable humidity (45%).",
        "typical_readings": {
            "pm25": 5.2,
            "co2": 450.0,
            "temperature": 22.0,
            "humidity": 45.0,
            "tvoc": 0.08,
            "co": 0.3,
        },
    },
    SCENARIO_COOKING: {
        "id": SCENARIO_COOKING,
        "name": "Kitchen Cooking Event",
        "description": "High heat cooking / pan frying generates sharp spikes in particulate matter (PM2.5 up to 80-150 µg/m³), TVOCs, and minor heat/CO emission.",
        "typical_readings": {
            "pm25": 115.0,
            "co2": 620.0,
            "temperature": 24.8,
            "humidity": 52.0,
            "tvoc": 2.2,
            "co": 2.1,
        },
    },
    SCENARIO_OUTDOOR_POLLUTION: {
        "id": SCENARIO_OUTDOOR_POLLUTION,
        "name": "Outdoor Pollution Infiltration",
        "description": "Smog or wildfire smoke seeping in through windows, steadily raising PM2.5 from 30 up to 80+ µg/m³ while CO2 remains standard.",
        "typical_readings": {
            "pm25": 78.5,
            "co2": 480.0,
            "temperature": 21.5,
            "humidity": 42.0,
            "tvoc": 0.35,
            "co": 0.6,
        },
    },
    SCENARIO_LOW_HUMIDITY: {
        "id": SCENARIO_LOW_HUMIDITY,
        "name": "Low Humidity / Dry Heating",
        "description": "Winter heating drives relative humidity down to 20-30%, causing respiratory irritation and dry skin risks.",
        "typical_readings": {
            "pm25": 7.0,
            "co2": 490.0,
            "temperature": 23.5,
            "humidity": 24.0,
            "tvoc": 0.12,
            "co": 0.4,
        },
    },
    SCENARIO_POOR_VENTILATION: {
        "id": SCENARIO_POOR_VENTILATION,
        "name": "Poor Ventilation / High Occupancy",
        "description": "Enclosed space with closed doors/windows and human occupants; CO2 rises steadily from 800 to 2000+ ppm, causing lethargy.",
        "typical_readings": {
            "pm25": 12.0,
            "co2": 1950.0,
            "temperature": 23.8,
            "humidity": 56.0,
            "tvoc": 0.75,
            "co": 0.5,
        },
    },
    SCENARIO_IMPROVEMENT: {
        "id": SCENARIO_IMPROVEMENT,
        "name": "Air Recovery & Purifier Active",
        "description": "Smart air purifiers and fresh air mechanical ventilation engage, progressively scrubbing particulates and balancing CO2 and humidity back to baseline.",
        "typical_readings": {
            "pm25": 8.5,
            "co2": 520.0,
            "temperature": 21.8,
            "humidity": 46.0,
            "tvoc": 0.14,
            "co": 0.3,
        },
    },
}


def calculate_aqi(pm25: float) -> tuple[int, str]:
    """Calculate US EPA standard Air Quality Index based on PM2.5 concentration."""
    pm = max(0.0, float(pm25))
    if pm <= 12.0:
        # 0 to 50
        aqi = round((50.0 / 12.0) * pm)
        status = "Good"
    elif pm <= 35.4:
        # 51 to 100
        aqi = round(51 + ((100 - 51) / (35.4 - 12.1)) * (pm - 12.1))
        status = "Moderate"
    elif pm <= 55.4:
        # 101 to 150
        aqi = round(101 + ((150 - 101) / (55.4 - 35.5)) * (pm - 35.5))
        status = "Unhealthy for Sensitive Groups"
    elif pm <= 150.4:
        # 151 to 200
        aqi = round(151 + ((200 - 151) / (150.4 - 55.5)) * (pm - 55.5))
        status = "Unhealthy"
    elif pm <= 250.4:
        # 201 to 300
        aqi = round(201 + ((300 - 201) / (250.4 - 150.5)) * (pm - 150.5))
        status = "Very Unhealthy"
    else:
        # 301 to 500
        aqi = min(500, round(301 + ((500 - 301) / (500.4 - 250.5)) * (pm - 250.5)))
        status = "Hazardous"
    return aqi, status


def generate_reading(
    scenario: str = SCENARIO_NORMAL,
    step: int = 0,
    room_id: int = 1,
    sensor_id: Optional[int] = 1,
    timestamp: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Generate a single air quality telemetry reading with scenario progression and natural noise.

    Args:
        scenario: One of the 5+ supported scenarios.
        step: Timeline progression counter (0 to N), controls curve evolution.
        room_id: ID of the room being measured.
        sensor_id: Associated sensor ID.
        timestamp: Measurement timestamp (defaults to current UTC).

    Returns:
        dict with all measurement fields: pm25, co2, temperature, humidity, tvoc, co, timestamp, etc.
    """
    if timestamp is None:
        timestamp = datetime.utcnow()

    # Step factor bounded [0.0, 1.0] for gradual progression over ~10-15 steps
    progression = min(1.0, max(0.0, step / 12.0))
    noise = lambda scale=1.0: random.uniform(-scale, scale)

    # Base healthy targets
    pm25 = 5.0 + noise(1.2)
    co2 = 450.0 + noise(20.0)
    temperature = 22.0 + noise(0.4)
    humidity = 45.0 + noise(1.5)
    tvoc = 0.08 + abs(noise(0.04))
    co = 0.3 + abs(noise(0.15))

    scenario_clean = scenario.lower().strip()

    if scenario_clean == SCENARIO_COOKING:
        # PM2.5 spikes rapidly to 80-150; temperature rises 2-3 C; TVOC spikes; CO slightly elevated
        spike_multiplier = math.sin(min(math.pi * 0.9, progression * math.pi * 0.75 + 0.2))
        pm25 = 15.0 + (125.0 * spike_multiplier) + noise(7.5)
        temperature = 22.0 + (3.0 * progression) + noise(0.3)
        humidity = 45.0 + (8.0 * progression) + noise(1.0)
        tvoc = 0.15 + (2.4 * spike_multiplier) + abs(noise(0.2))
        co = 0.4 + (2.0 * spike_multiplier) + abs(noise(0.3))

    elif scenario_clean == SCENARIO_OUTDOOR_POLLUTION:
        # PM2.5 rises steadily 30 -> 80+, CO2 stays normal
        pm25 = 30.0 + (52.0 * progression) + noise(4.0)
        co2 = 450.0 + noise(15.0)
        temperature = 21.5 + noise(0.3)
        humidity = 42.0 + noise(1.2)
        tvoc = 0.18 + (0.25 * progression) + abs(noise(0.05))
        co = 0.5 + noise(0.1)

    elif scenario_clean == SCENARIO_LOW_HUMIDITY:
        # Humidity drops to 20-30%, other readings normal
        target_humidity = 45.0 - (21.0 * progression)
        humidity = max(18.0, target_humidity + noise(1.5))
        temperature = 23.2 + noise(0.3)
        pm25 = 6.5 + noise(1.0)
        co2 = 470.0 + noise(25.0)
        tvoc = 0.10 + abs(noise(0.03))
        co = 0.3 + noise(0.1)

    elif scenario_clean == SCENARIO_POOR_VENTILATION:
        # CO2 rises 800 -> 2000, other readings normal
        co2 = 800.0 + (1200.0 * progression) + noise(45.0)
        humidity = 46.0 + (9.0 * progression) + noise(1.2)  # human exhalation
        temperature = 22.5 + (1.2 * progression) + noise(0.2)
        pm25 = 7.0 + noise(1.5)
        tvoc = 0.20 + (0.55 * progression) + abs(noise(0.05))
        co = 0.4 + noise(0.1)

    elif scenario_clean == SCENARIO_IMPROVEMENT:
        # Values gradually decay from previous elevated levels back to normal
        decay = 1.0 - progression
        pm25 = 5.0 + (55.0 * decay) + noise(1.0)
        co2 = 450.0 + (750.0 * decay) + noise(18.0)
        humidity = 45.0 - (15.0 * decay) + noise(1.0)
        temperature = 22.0 + (1.5 * decay) + noise(0.2)
        tvoc = 0.08 + (0.8 * decay) + abs(noise(0.03))
        co = 0.3 + (1.2 * decay) + abs(noise(0.1))

    # Guard negative values and round sensibly
    pm25 = round(max(0.5, pm25), 1)
    co2 = round(max(350.0, co2), 0)
    temperature = round(temperature, 1)
    humidity = round(min(100.0, max(5.0, humidity)), 1)
    tvoc = round(max(0.01, tvoc), 2)
    co = round(max(0.0, co), 1)

    aqi, aqi_status = calculate_aqi(pm25)

    return {
        "sensor_id": sensor_id,
        "room_id": room_id,
        "pm25": pm25,
        "co2": co2,
        "temperature": temperature,
        "humidity": humidity,
        "tvoc": tvoc,
        "co": co,
        "aqi": aqi,
        "aqi_status": aqi_status,
        "timestamp": timestamp,
        "is_simulated": True,
        "scenario": scenario_clean,
    }


def generate_history(
    hours: int = 24,
    scenario: str = SCENARIO_NORMAL,
    room_id: int = 1,
    sensor_id: Optional[int] = 1,
    interval_minutes: int = 30,
) -> List[Dict[str, Any]]:
    """Generate chronological time-series measurements over the past N hours.

    Args:
        hours: Number of past hours to generate.
        scenario: Base simulation scenario.
        room_id: Room ID to associate.
        sensor_id: Sensor ID to associate.
        interval_minutes: Frequency between generated points.

    Returns:
        List of measurement dicts ordered from oldest to newest.
    """
    now = datetime.utcnow()
    total_steps = max(1, int((hours * 60) / interval_minutes))
    history: List[Dict[str, Any]] = []

    for i in range(total_steps):
        time_offset = timedelta(minutes=(total_steps - 1 - i) * interval_minutes)
        point_time = now - time_offset

        # Cyclic diurnal variations for natural realism
        # E.g. temperature slightly warmer in afternoon, CO2 rises during evening hours
        hour_of_day = point_time.hour
        diurnal_temp = math.sin((hour_of_day - 8) * math.pi / 12) * 1.5
        diurnal_co2 = math.cos((hour_of_day - 20) * math.pi / 12) * 60

        # Step value mapped into scenario progression
        step_val = i % 15
        reading = generate_reading(
            scenario=scenario,
            step=step_val,
            room_id=room_id,
            sensor_id=sensor_id,
            timestamp=point_time,
        )

        # Apply slight diurnal touch
        reading["temperature"] = round(reading["temperature"] + diurnal_temp, 1)
        reading["co2"] = round(reading["co2"] + diurnal_co2, 0)
        history.append(reading)

    return history
