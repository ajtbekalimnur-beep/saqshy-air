"""AI Assistant Service for SAQSHY AIR — Groq API + rule-based fallback."""

import logging
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("saqshy.ai")

GROQ_MODEL = "qwen/qwen3.8-27b"


def _format_context(ctx: Optional[Dict[str, Any]]) -> str:
    if not ctx:
        return "No sensor data available."
    lines = []
    if "room_name" in ctx:
        lines.append(f"Room: {ctx['room_name']}")
    for k, unit in [("pm25", "µg/m³"), ("co2", "ppm"), ("temperature", "°C"), ("humidity", "%"), ("tvoc", "mg/m³"), ("co", "ppm")]:
        if k in ctx:
            lines.append(f"  {k.upper()}: {ctx[k]} {unit}")
    return "\n".join(lines)


def _rule_response(msg: str, ctx: Optional[Dict[str, Any]] = None) -> str:
    """High-quality rule-based fallback responses."""
    m = msg.lower()
    c = ctx or {}
    pm25 = c.get("pm25", 8.0)
    co2  = c.get("co2", 500.0)
    hum  = c.get("humidity", 45.0)
    temp = c.get("temperature", 22.0)
    co   = c.get("co", 0.2)
    room = c.get("room_name", "your room")

    dis = ("\n\n*SAQSHY AIR is an environmental monitor, not a medical device. "
           "For health concerns consult a medical professional.*")

    # CO emergency
    if co > 25:
        return (f"🚨 **CRITICAL: CO = {co} ppm** — EVACUATE IMMEDIATELY.\n\n"
                "Leave the building now, call emergency services (112/911). Do NOT re-enter until cleared.")
    if co > 9 or "carbon monoxide" in m:
        return (f"⚠️ **Elevated CO: {co} ppm** (safe < 9 ppm).\n\n"
                "Open windows, leave the area, check gas appliances, call professionals if CO stays elevated.")

    if any(w in m for w in ["pm2.5","pm25","particulate","dust","particle","smoke"]):
        s = "✅ Good" if pm25<12 else ("⚠️ Moderate" if pm25<35 else "🔴 Elevated")
        return (f"### PM2.5 — {pm25} µg/m³ ({s})\n\n"
                "**Guidelines:** WHO 24h = 15 µg/m³ | Good <12 | Moderate 12–35 | Unhealthy >35\n\n"
                "**Common indoor sources:** cooking, candles, cleaning, outdoor infiltration.\n\n"
                f"**Recommendation:** {'Air purifier with HEPA recommended.' if pm25>35 else 'No action needed, continue monitoring.'}" + dis)

    if any(w in m for w in ["co2","carbon dioxide","ventilat","stuffy","drowsy","brain fog"]):
        s = "✅ Fresh" if co2<800 else ("⚠️ Acceptable" if co2<1000 else "🔴 Poor ventilation")
        return (f"### CO₂ — {co2} ppm ({s})\n\n"
                "**Scale:** <800 Fresh | 800–1000 OK | 1000–1500 Stale | >1500 Very poor\n\n"
                "⚠️ CO₂ ≠ CO. CO₂ is a ventilation indicator. CO is a toxic gas needing its own certified detector.\n\n"
                f"**Recommendation:** {'Open windows or run ventilation.' if co2>900 else 'Ventilation is good.'}" + dis)

    if any(w in m for w in ["humid","dry","moisture","mold","humidifier","dehumidifier"]):
        s = "🔴 Very dry" if hum<25 else ("⚠️ Dry" if hum<35 else ("✅ Optimal" if hum<=60 else ("⚠️ High" if hum<=70 else "🔴 Very High")))
        rec = ("Use a humidifier, target 40–50%." if hum<35 else
               ("Use a dehumidifier or improve ventilation." if hum>65 else "No action needed."))
        return (f"### Humidity — {hum}% ({s})\n\n"
                "**Optimal: 40–60%** | <30% dry irritation risk | >65% mold risk\n\n"
                f"**Recommendation:** {rec}" + dis)

    if any(w in m for w in ["window","open","outdoor","outside","fresh air"]):
        return (f"### Should you open the window?\n\n"
                f"Indoor: PM2.5={pm25} µg/m³, CO₂={co2} ppm, Humidity={hum}%\n\n"
                "✅ **Open** when: CO₂ elevated + outdoor air is clean; indoor humidity high + outdoor is drier\n\n"
                "❌ **Keep closed** when: outdoor PM2.5 > indoor; wildfire/smog event; outdoor humidity very high\n\n"
                f"**Now:** {'CO₂ elevated — ventilation recommended if outdoor conditions allow.' if co2>900 else 'Air is fresh — no urgent need.'}" + dis)

    if any(w in m for w in ["purifier","hepa","filter","equipment","humidifier","dehumidifier"]):
        return (f"### Equipment Advisory ({room})\n\n"
                f"- **Air Purifier (HEPA):** {'🔴 Recommended HIGH — PM2.5 elevated.' if pm25>35 else '🟢 ECO/AUTO is fine.'}\n"
                f"- **Ventilation:** {'🔴 Increase — CO₂ elevated.' if co2>1000 else '🟢 Normal setting OK.'}\n"
                f"- **Humidifier:** {'🔴 ON — target 45%.' if hum<35 else ('🔴 OFF — humidity already high.' if hum>65 else '🟢 Not needed.')}" + dis)

    if any(w in m for w in ["bedroom","sleep","night"]):
        return ("### Bedroom Air Quality Tips\n\n"
                "🌙 **Before sleep:** ventilate 10–15 min if outdoor conditions allow; target CO₂ < 800 ppm\n\n"
                "🛏️ **Ongoing:** wash bedding regularly, avoid candles/incense, keep humidity 40–55%\n\n"
                "📡 Add a dedicated bedroom sensor for accurate overnight monitoring." + dis)

    # Default
    return (f"Hello! I'm **SAQSHY AI** — your indoor air quality assistant.\n\n"
            f"**Current readings in {room}:**\n"
            f"- PM2.5: **{pm25} µg/m³**\n- CO₂: **{co2} ppm**\n"
            f"- Humidity: **{hum}%**\n- Temperature: **{temp}°C**\n\n"
            "Ask me: *'Why is PM2.5 high?'*, *'Should I open the window?'*, "
            "*'What is CO₂ vs CO?'*, *'When to use the air purifier?'*" + dis)


def get_ai_response(
    user_message: str,
    sensor_context: Optional[Dict[str, Any]] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> str:
    """Get response from Groq (llama-3.3-70b) with rule-based fallback."""
    api_key = os.getenv("GROQ_API_KEY", "").strip()

    if not api_key or api_key in ("your_key_here", "placeholder", ""):
        logger.info("No Groq API key — using rule-based fallback.")
        return _rule_response(user_message, sensor_context)

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        system = (
            "You are SAQSHY AI — an expert indoor air quality assistant. "
            "Help users understand PM2.5, CO2, temperature, humidity, TVOC, CO. "
            "RULES: 1) Never claim to be a medical device. 2) If CO >= 25 ppm, give CRITICAL EVACUATION warning. "
            "3) Reference the live sensor data below. 4) Be concise and use markdown. "
            "5) Distinguish between measured facts, general knowledge, and hypotheses.\n\n"
            f"LIVE SENSOR DATA:\n{_format_context(sensor_context)}\n\n"
            "THRESHOLDS: PM2.5 Good<12, Moderate 12-35, Unhealthy>35, Hazardous>75 µg/m³ | "
            "CO2 Fresh<800, OK 800-1000, Poor>1000, Severe>2000 ppm | "
            "Humidity Optimal 40-60%, Dry<30%, Mold risk>65% | CO Safe<9ppm, Danger>9ppm"
        )

        msgs: List[Dict[str, str]] = [{"role": "system", "content": system}]
        for h in (conversation_history or [])[-6:]:
            if h.get("role") in ("user", "assistant") and h.get("content"):
                msgs.append({"role": h["role"], "content": h["content"]})
        msgs.append({"role": "user", "content": user_message})

        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=msgs,
            max_tokens=900,
            temperature=0.65,
        )
        text = resp.choices[0].message.content or ""
        logger.info(f"Groq response: {len(text)} chars")
        return text if text.strip() else _rule_response(user_message, sensor_context)

    except Exception as e:
        logger.warning(f"Groq API error, using fallback: {e}")
        return _rule_response(user_message, sensor_context)


def analyze_pollution_sources(readings: Dict[str, Any], room_name: str = "Living Room") -> Dict[str, Any]:
    """Rule-based source analysis returning hypotheses with confidence scores."""
    pm25 = float(readings.get("pm25", 8.0))
    co2  = float(readings.get("co2", 500.0))
    hum  = float(readings.get("humidity", 45.0))
    temp = float(readings.get("temperature", 22.0))
    tvoc = float(readings.get("tvoc", 0.1))
    co   = float(readings.get("co", 0.2))

    hypotheses, evidence, recommendations = [], [], []

    if pm25 > 75:
        evidence.append(f"Severe PM2.5 spike: {pm25} µg/m³ (WHO 24h: 15 µg/m³)")
    elif pm25 > 35:
        evidence.append(f"Elevated PM2.5: {pm25} µg/m³")
    if co2 > 1200:
        evidence.append(f"CO2 elevated: {co2} ppm — insufficient fresh air")
    if tvoc > 0.8:
        evidence.append(f"High TVOC: {tvoc} mg/m³")
    if hum < 30:
        evidence.append(f"Very dry air: {hum}%")
    elif hum > 65:
        evidence.append(f"High humidity: {hum}%")
    if co > 5:
        evidence.append(f"CO detected: {co} ppm")

    if pm25 > 60 and (tvoc > 0.8 or temp > 23.5):
        hypotheses.append({"hypothesis": "Cooking / Frying", "likelihood": "High", "probability": 0.88,
            "reason": "PM2.5 spike + elevated TVOC/temperature matches cooking combustion signature."})
        recommendations += ["Run kitchen range hood on high.", "Activate HEPA purifier on TURBO."]

    if pm25 > 40 and co2 < 700 and tvoc < 0.4:
        hypotheses.append({"hypothesis": "Outdoor Pollution Infiltration", "likelihood": "High", "probability": 0.82,
            "reason": "High PM2.5 with low CO2/TVOC indicates outdoor particulates entering through windows/gaps."})
        recommendations += ["Close exterior windows.", "Run air purifier on medium continuously."]

    if co2 > 1000 and pm25 < 30:
        hypotheses.append({"hypothesis": "Poor Ventilation / High Occupancy", "likelihood": "Very High", "probability": 0.94,
            "reason": "CO2 elevated while PM2.5 is low — classic human respiration in enclosed space."})
        recommendations += ["Open windows for 10–15 min cross-ventilation.", "Increase HRV fan speed."]

    if tvoc > 1.0 and pm25 < 30:
        hypotheses.append({"hypothesis": "Chemical Off-gassing / Cleaning Products", "likelihood": "High", "probability": 0.85,
            "reason": "High TVOC without PM2.5 spike suggests solvents, sprays or new furniture off-gassing."})
        recommendations += ["Ventilate room immediately.", "Use activated carbon filter."]

    if hum < 30:
        hypotheses.append({"hypothesis": "Heating System Over-Drying Air", "likelihood": "High", "probability": 0.89,
            "reason": "Very low humidity consistent with central heating without humidification."})
        recommendations.append("Run humidifier, target 40–50% RH.")

    if not hypotheses:
        hypotheses.append({"hypothesis": "Normal Baseline — No Issues Detected", "likelihood": "High", "probability": 0.95,
            "reason": "All readings within healthy ranges."})
        evidence.append("All sensors within WHO/EPA guidelines.")
        recommendations.append("No action needed. Continue monitoring.")

    return {
        "room_name": room_name,
        "hypotheses": hypotheses,
        "confidence": max(h["probability"] for h in hypotheses),
        "evidence": evidence,
        "recommendations": recommendations,
    }
