"""Pydantic schemas and DTOs for SAQSHY AIR backend."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------
# Room Schemas
# ---------------------------------------------------------
class RoomBase(BaseModel):
    name: str = Field(..., example="Living Room")
    type: str = Field(default="living_room", example="living_room")
    floor: int = Field(default=1, example=1)


class RoomCreate(RoomBase):
    pass


class RoomUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    floor: Optional[int] = None


class RoomResponse(RoomBase):
    id: int
    created_at: datetime
    sensors_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# Sensor Schemas
# ---------------------------------------------------------
class SensorBase(BaseModel):
    name: str = Field(..., example="Living Room Air Sentinel")
    type: str = Field(default="multi_sensor", example="multi_sensor")
    status: str = Field(default="online", example="online")
    battery_level: int = Field(default=100, ge=0, le=100)
    is_simulated: bool = Field(default=True)


class SensorCreate(SensorBase):
    room_id: Optional[int] = None


class SensorUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    battery_level: Optional[int] = None
    room_id: Optional[int] = None
    is_simulated: Optional[bool] = None


class SensorResponse(SensorBase):
    id: int
    room_id: Optional[int] = None
    last_seen: datetime

    model_config = ConfigDict(from_attributes=True)


class SensorStatusResponse(BaseModel):
    id: int
    name: str
    room_id: Optional[int]
    room_name: Optional[str] = None
    type: str
    status: str
    battery_level: int
    last_seen: datetime
    is_simulated: bool
    ping_ms: int = 15

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# Measurement Schemas
# ---------------------------------------------------------
class MeasurementBase(BaseModel):
    room_id: int
    pm25: float = Field(..., description="PM2.5 in ug/m3", example=8.5)
    co2: float = Field(..., description="CO2 in ppm", example=520.0)
    temperature: float = Field(..., description="Temperature in Celsius", example=22.3)
    humidity: float = Field(..., description="Relative humidity in %", example=44.2)
    tvoc: float = Field(default=0.1, description="TVOC in mg/m3", example=0.15)
    co: float = Field(default=0.0, description="Carbon monoxide in ppm", example=0.2)


class MeasurementCreate(MeasurementBase):
    sensor_id: Optional[int] = None
    is_simulated: bool = False
    scenario: str = "normal"
    timestamp: Optional[datetime] = None


class MeasurementResponse(MeasurementBase):
    id: int
    sensor_id: Optional[int] = None
    timestamp: datetime
    is_simulated: bool
    scenario: str

    model_config = ConfigDict(from_attributes=True)


class CurrentRoomReading(BaseModel):
    room_id: int
    room_name: str
    room_type: str
    pm25: float
    co2: float
    temperature: float
    humidity: float
    tvoc: float
    co: float
    aqi: int
    aqi_status: str  # Good, Moderate, Unhealthy for Sensitive Groups, Unhealthy, Very Unhealthy, Hazardous
    timestamp: datetime
    sensor_status: str


# ---------------------------------------------------------
# Equipment Schemas
# ---------------------------------------------------------
class EquipmentBase(BaseModel):
    name: str = Field(..., example="Smart HEPA Air Purifier Pro")
    category: str = Field(..., example="purifier")  # purifier, humidifier, dehumidifier, ventilation, ac
    status: str = Field(default="idle", example="idle")  # running, idle, off, maintenance
    mode: str = Field(default="auto", example="auto")    # auto, manual, eco, turbo


class EquipmentCreate(EquipmentBase):
    room_id: int


class EquipmentUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    mode: Optional[str] = None
    room_id: Optional[int] = None


class EquipmentResponse(EquipmentBase):
    id: int
    room_id: int
    last_maintenance: datetime

    model_config = ConfigDict(from_attributes=True)


class EquipmentWithRecommendation(EquipmentResponse):
    room_name: Optional[str] = None
    recommended_status: Optional[str] = None
    recommended_mode: Optional[str] = None
    reason: Optional[str] = None


# ---------------------------------------------------------
# Recommendation & Alert Schemas
# ---------------------------------------------------------
class RecommendationResponse(BaseModel):
    id: int
    room_id: Optional[int] = None
    room_name: Optional[str] = None
    type: str
    severity: str  # info, warning, danger, critical
    title: str
    description: str
    action: Optional[str] = None
    created_at: datetime
    resolved: bool

    model_config = ConfigDict(from_attributes=True)


class AlertResponse(BaseModel):
    id: int
    room_id: Optional[int] = None
    room_name: Optional[str] = None
    type: str
    severity: str  # warning, danger, critical
    title: str
    message: str
    created_at: datetime
    resolved: bool

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# Conversation & AI Chat Schemas
# ---------------------------------------------------------
class MessageBase(BaseModel):
    role: str
    content: str


class MessageCreate(BaseModel):
    content: str
    role: str = "user"


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    message_count: int = 0
    last_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    messages: List[MessageResponse]

    model_config = ConfigDict(from_attributes=True)


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None
    include_sensor_context: bool = True


class ChatResponse(BaseModel):
    response: str
    conversation_id: int
    context_used: Optional[Dict[str, Any]] = None


class SourceHypothesis(BaseModel):
    hypothesis: str
    likelihood: str  # Low, Medium, High, Very High
    probability: float
    reason: str


class SourceAnalysisRequest(BaseModel):
    room_id: Optional[int] = None


class SourceAnalysisResponse(BaseModel):
    room_id: Optional[int] = None
    room_name: Optional[str] = None
    hypotheses: List[SourceHypothesis]
    confidence: float
    evidence: List[str]
    recommendations: List[str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------
# Demo Schemas
# ---------------------------------------------------------
class DemoScenario(BaseModel):
    id: str
    name: str
    description: str
    typical_readings: Dict[str, Any]


class DemoStatusResponse(BaseModel):
    active_scenario: str
    step: int
    is_active: bool
    updated_at: datetime


# ---------------------------------------------------------
# Reports Schemas
# ---------------------------------------------------------
class DailyReportResponse(BaseModel):
    date: str
    avg_pm25: float
    max_pm25: float
    avg_co2: float
    max_co2: float
    avg_temp: float
    avg_humidity: float
    air_quality_score: int
    healthy_hours: float
    anomalies_detected: int
    summary: str


class WeeklyDaySummary(BaseModel):
    date: str
    day_name: str
    avg_pm25: float
    avg_co2: float
    air_quality_score: int
    status: str


class WeeklyReportResponse(BaseModel):
    period: str
    average_score: int
    best_day: str
    worst_day: str
    total_anomalies: int
    estimated_filter_life_percent: int
    energy_efficiency_index: str
    days: List[WeeklyDaySummary]
    executive_summary: str
