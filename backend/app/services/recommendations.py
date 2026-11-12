"""Rule-based indoor air quality recommendation and alert engine."""

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models import Alert, Recommendation


def analyze_readings(readings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Analyze environmental telemetry against thresholds and return recommendations.

    Rules implemented:
    - Special CO: CO > 25 ppm = CRITICAL emergency, CO > 9 ppm = DANGER
    - PM2.5 > 75 = DANGER, PM2.5 > 35 = WARNING
    - CO2 > 2000 = DANGER, CO2 > 1000 = WARNING
    - Humidity < 30 = LOW (warning), Humidity > 65 = HIGH (warning)
    - Temp < 18 = COLD (info), Temp > 26 = WARM (info)
    - TVOC > 1.0 = WARNING

    Returns:
        List of recommendation dictionaries: {type, severity, title, description, action}
    """
    pm25 = float(readings.get("pm25", 0.0))
    co2 = float(readings.get("co2", 0.0))
    temp = float(readings.get("temperature", 22.0))
    humidity = float(readings.get("humidity", 45.0))
    tvoc = float(readings.get("tvoc", 0.0))
    co = float(readings.get("co", 0.0))

    recommendations: List[Dict[str, Any]] = []

    # 1. Carbon Monoxide (Life Safety Critical)
    if co > 25.0:
        recommendations.append({
            "type": "safety",
            "severity": "critical",
            "title": "CRITICAL EMERGENCY: Dangerous Carbon Monoxide Level",
            "description": f"Carbon monoxide is {co:.1f} ppm! Extremely hazardous condition with severe poisoning risk.",
            "action": "EVACUATE IMMEDIATELY. Extinguish all combustion appliances, open doors/windows if safe on exit, and contact emergency services.",
        })
    elif co > 9.0:
        recommendations.append({
            "type": "safety",
            "severity": "danger",
            "title": "Elevated Carbon Monoxide (CO) Alert",
            "description": f"CO concentration reached {co:.1f} ppm (safe indoor limit is 9 ppm). Potential stove, heater, or flue leak.",
            "action": "Ventilate immediately, turn off unvented gas or fuel heaters, and inspect combustion sources.",
        })

    # 2. Particulate Matter (PM2.5)
    if pm25 > 75.0:
        recommendations.append({
            "type": "purification",
            "severity": "danger",
            "title": "Hazardous Particulate Level (PM2.5)",
            "description": f"PM2.5 reading is {pm25:.1f} µg/m³, which is 5x above healthy targets. Respiratory irritation likely.",
            "action": "Set HEPA air purifiers to Turbo speed immediately and verify external windows are sealed.",
        })
    elif pm25 > 35.0:
        recommendations.append({
            "type": "purification",
            "severity": "warning",
            "title": "Elevated Particulate Level (PM2.5)",
            "description": f"PM2.5 reading is {pm25:.1f} µg/m³. Moderately unhealthy for sensitive individuals and children.",
            "action": "Run air purifier on Medium/High mode until PM2.5 drops below 15 µg/m³.",
        })

    # 3. Carbon Dioxide (CO2)
    if co2 > 2000.0:
        recommendations.append({
            "type": "ventilation",
            "severity": "danger",
            "title": "Severe CO2 Accumulation",
            "description": f"Carbon dioxide reached {co2:.0f} ppm. Triggers headaches, sleepiness, and significantly reduced mental clarity.",
            "action": "Open windows widely for 15-minute cross-ventilation or boost mechanical HRV/ERV ventilation to maximum.",
        })
    elif co2 > 1000.0:
        recommendations.append({
            "type": "ventilation",
            "severity": "warning",
            "title": "Stale Indoor Air (High CO2)",
            "description": f"CO2 concentration is {co2:.0f} ppm. Air is getting stuffy and may impair focus.",
            "action": "Crack open a window or door for 10 minutes to introduce fresh outdoor oxygen.",
        })

    # 4. Humidity
    if humidity < 30.0:
        recommendations.append({
            "type": "humidity",
            "severity": "warning",
            "title": "Low Air Humidity",
            "description": f"Relative humidity is {humidity:.1f}%. Dry air dehydrates mucous membranes and prolongs airborne virus suspension.",
            "action": "Activate ultrasonic humidifier to bring humidity back into the 40-50% target band.",
        })
    elif humidity > 65.0:
        recommendations.append({
            "type": "humidity",
            "severity": "warning",
            "title": "High Air Humidity (Mold Risk)",
            "description": f"Relative humidity is {humidity:.1f}%. High moisture accelerates mold growth and dust mite propagation.",
            "action": "Activate dehumidifier or set AC to dry mode until humidity falls below 55%.",
        })

    # 5. Temperature
    if temp < 18.0:
        recommendations.append({
            "type": "temperature",
            "severity": "info",
            "title": "Cold Room Temperature",
            "description": f"Temperature is {temp:.1f}°C, below comfortable living conditions (20-22°C).",
            "action": "Adjust heating setpoint to 21°C.",
        })
    elif temp > 26.0:
        recommendations.append({
            "type": "temperature",
            "severity": "info",
            "title": "Warm Room Temperature",
            "description": f"Temperature is {temp:.1f}°C, which may cause thermal discomfort or restless sleep.",
            "action": "Lower blinds to block sun or engage air cooling.",
        })

    # 6. TVOC
    if tvoc > 1.0:
        recommendations.append({
            "type": "safety",
            "severity": "warning",
            "title": "High Chemical Volatiles (TVOC)",
            "description": f"TVOC level is {tvoc:.2f} mg/m³. Common with cooking fumes, air fresheners, solvents, or new furniture off-gassing.",
            "action": "Ventilate the space and enable activated carbon filter on your air purifier.",
        })

    # If no warnings triggered, provide positive assurance
    if not recommendations:
        recommendations.append({
            "type": "general",
            "severity": "info",
            "title": "Optimal Air Quality",
            "description": "All monitored indoor air parameters are within clean, healthy standard thresholds.",
            "action": "Maintain current ventilation and air purification settings.",
        })

    return recommendations


def sync_recommendations_and_alerts_to_db(
    db: Session,
    room_id: int,
    readings: Dict[str, Any],
) -> List[Recommendation]:
    """Evaluate readings and sync newly triggered recommendations/alerts into the DB."""
    recs = analyze_readings(readings)
    created_recs: List[Recommendation] = []

    for r in recs:
        # Avoid spamming duplicates if an identical unresolved recommendation exists
        existing = (
            db.query(Recommendation)
            .filter(
                Recommendation.room_id == room_id,
                Recommendation.title == r["title"],
                Recommendation.resolved == False,
            )
            .first()
        )
        if not existing:
            db_rec = Recommendation(
                room_id=room_id,
                type=r["type"],
                severity=r["severity"],
                title=r["title"],
                description=r["description"],
                action=r["action"],
                resolved=False,
            )
            db.add(db_rec)
            created_recs.append(db_rec)

        # Critical / danger alerts saved to Alert table
        if r["severity"] in ("critical", "danger"):
            existing_alert = (
                db.query(Alert)
                .filter(
                    Alert.room_id == room_id,
                    Alert.title == r["title"],
                    Alert.resolved == False,
                )
                .first()
            )
            if not existing_alert:
                db_alert = Alert(
                    room_id=room_id,
                    type=r["type"],
                    severity=r["severity"],
                    title=r["title"],
                    message=r["description"],
                    resolved=False,
                )
                db.add(db_alert)

    db.commit()
    return created_recs
