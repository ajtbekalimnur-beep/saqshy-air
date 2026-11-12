# SAQSHY AIR — AI-Powered Indoor Air Intelligence Platform

<div align="center">

```
  ╔══════════════════════════════════════╗
  ║        💨  SAQSHY AIR  💨            ║
  ║   AI Indoor Environmental Platform   ║
  ╚══════════════════════════════════════╝
```

**MVP v1.0 — Competition Ready**

</div>

---

## 🚀 Quick Start (3 minutes)

### Option A — Frontend Only (No Installation Required)

The simplest way to run SAQSHY AIR — just open the HTML file:

```
frontend/index.html  →  Double-click to open in browser
```

The app works **completely without the backend** in Demo Mode with simulated sensors.

---

### Option B — Full Stack (Frontend + FastAPI Backend)

#### Prerequisites
- Python 3.10+ ([python.org](https://python.org))
- pip (included with Python)

#### Step 1 — Install backend dependencies

```powershell
cd backend
pip install -r requirements.txt
```

#### Step 2 — Configure environment

```powershell
copy .env.example .env
```

Edit `.env` and add your Anthropic API key (optional — the app works without it):
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

#### Step 3 — Start the backend

```powershell
# From the backend/ directory:
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Or use the startup script from the project root:
.\start-backend.ps1
```

#### Step 4 — Open the frontend

Open `frontend/index.html` in your browser.

Go to **Settings** → set Backend URL to `http://localhost:8000`

---

## 📋 Project Structure

```
saqshy-air/
├── frontend/
│   └── index.html              ← Complete web application (single file)
│
├── backend/
│   ├── requirements.txt        ← Python dependencies
│   ├── .env.example            ← Environment variables template
│   ├── .env                    ← Your local config (not committed)
│   └── app/
│       ├── main.py             ← FastAPI application entry point
│       ├── database.py         ← SQLAlchemy SQLite setup
│       ├── models.py           ← Database models
│       ├── schemas.py          ← Pydantic validation schemas
│       ├── seed_data.py        ← Demo data seeder
│       ├── services/
│       │   ├── ai_service.py        ← Claude AI + rule-based fallback
│       │   ├── simulator.py         ← Sensor data simulation engine
│       │   └── recommendations.py  ← Rule-based recommendation engine
│       └── routers/
│           ├── sensors.py      ← GET/POST sensor data endpoints
│           ├── ai.py           ← AI chat and source analysis
│           ├── demo.py         ← Demo scenario controller
│           ├── rooms.py        ← Room management
│           ├── equipment.py    ← Equipment management
│           └── reports.py      ← History and reports
│
├── start-backend.ps1           ← Windows startup script
└── README.md
```

---

## 🎯 Demo Mode — Competition Guide

**Demo Mode is ON by default.** The sidebar shows a toggle to enable/disable it.

### Running the 5 Demo Scenarios

Use the dropdown in the yellow banner at the top:

| Scenario | What it shows | Key measurements |
|----------|--------------|------------------|
| 🌿 Normal | Baseline healthy air | PM2.5 ~5, CO₂ ~450 |
| 🍳 Cooking Event | PM2.5 spike during cooking | PM2.5 rises to 60–150 µg/m³ |
| 🌫️ Outdoor Pollution | Particulates infiltrating indoors | PM2.5 rises steadily 35–85 |
| 💧 Low Humidity | Persistent dry air | Humidity drops to 18–28% |
| 🌬️ Poor Ventilation | CO₂ accumulation | CO₂ rises to 1200–2200 ppm |
| ✅ Air Improvement | Recovery after action | All values return to normal |

### Recommended Competition Demo Flow

1. **Open** `frontend/index.html` → Dashboard loads with healthy readings
2. **Switch scenario** → "🍳 Cooking Event"
3. Watch PM2.5 rise on the dashboard cards and charts
4. Navigate to **Source Intelligence** → Click "Run Analysis" → See cooking hypothesis
5. Navigate to **AI Assistant** → Ask: *"Why is my air quality getting worse?"*
6. Navigate to **Smart Equipment** → See Air Purifier recommendation triggered
7. Click "Simulate ON" on Air Purifier → PM2.5 drops
8. Navigate to **History & Reports** → Show improvement tracking
9. Navigate to **UV-C Education** → Explain technology

---

## 🔌 IoT Hardware Integration

Connect a real ESP32 sensor by POSTing to:

```
POST http://localhost:8000/api/sensors/reading
Content-Type: application/json

{
  "sensor_id": "node-01",
  "room": "living_room",
  "pm25": 12.5,
  "co2": 650,
  "temperature": 22.3,
  "humidity": 48,
  "timestamp": "2026-11-12T10:30:00Z"
}
```

**Recommended sensor hardware for first prototype:**
- PM2.5: PMS5003 or SPS30 (Sensirion)
- CO₂: SCD40 or SCD41 (NDIR — Sensirion) 
- Temperature + Humidity: SHT31 or DHT22
- Microcontroller: ESP32 (Wi-Fi built in)
- Protocol: HTTP POST over Wi-Fi (MQTT optional)

> ⚠️ **Important:** A TVOC sensor does not identify individual chemicals. A PM2.5 sensor does not measure gases. Use dedicated sensors for each measurement type.

---

## 🔑 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/sensors/current` | GET | Latest readings per room |
| `/api/sensors/history` | GET | Historical data (24h default) |
| `/api/sensors/reading` | POST | Ingest IoT sensor data |
| `/api/ai/chat` | POST | AI assistant chat |
| `/api/ai/analyze` | POST | Source intelligence analysis |
| `/api/demo/scenarios` | GET | List demo scenarios |
| `/api/demo/start/{id}` | POST | Start a demo scenario |
| `/api/demo/readings` | GET | Current demo readings |
| `/api/rooms/` | GET/POST | Room management |
| `/api/equipment/` | GET | Equipment list + recommendations |
| `/api/reports/daily` | GET | Today's summary |
| `/api/reports/weekly` | GET | 7-day summary |

Full interactive docs: `http://localhost:8000/docs`

---

## 🧪 Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5, CSS3, Vanilla JavaScript, Chart.js |
| Backend | Python 3.12, FastAPI, Uvicorn |
| Database | SQLite (file: `backend/saqshy.db`) |
| ORM | SQLAlchemy 2.0 (sync) |
| AI | Anthropic Claude API + rule-based fallback |
| IoT | HTTP/REST (MQTT-ready architecture) |

---

## ⚠️ Safety Disclaimers

- SAQSHY AIR is **not** a certified life-safety device
- Always maintain a **certified carbon monoxide alarm** independently
- Sensor readings in Demo Mode are **simulated** — not real measurements
- AI recommendations are informational — not medical advice
- Do not make health decisions based solely on this application

---

## 🏁 Built for Competition

SAQSHY AIR MVP was built to demonstrate the full product cycle:

**SENSORS → DATA → AI ANALYSIS → SOURCE DETECTION → RECOMMENDATIONS → RESULT VERIFICATION**

The demo mode allows judges to explore every feature without physical hardware.

---

*SAQSHY AIR · AI Environmental Intelligence Platform · MVP v1.0*
