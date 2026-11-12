"""SQLAlchemy models for SAQSHY AIR backend."""

from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Room(Base):
    """Room or indoor zone monitored by SAQSHY AIR."""
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False, default="living_room")  # living_room, bedroom, kitchen, children_room, office, etc.
    floor = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    sensors = relationship("Sensor", back_populates="room", cascade="all, delete-orphan")
    measurements = relationship("Measurement", back_populates="room", cascade="all, delete-orphan")
    equipment = relationship("Equipment", back_populates="room", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="room", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="room", cascade="all, delete-orphan")


class Sensor(Base):
    """IoT or simulated sensor node assigned to a room."""
    __tablename__ = "sensors"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False, default="multi_sensor")  # multi_sensor, pm25, co2, temp_humidity
    status = Column(String(20), default="online")  # online, offline, warning
    battery_level = Column(Integer, default=100)  # 0 - 100 percentage
    last_seen = Column(DateTime, default=datetime.utcnow)
    is_simulated = Column(Boolean, default=True)

    # Relationships
    room = relationship("Room", back_populates="sensors")
    measurements = relationship("Measurement", back_populates="sensor", cascade="all, delete-orphan")


class Measurement(Base):
    """Air quality environmental telemetry record."""
    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    pm25 = Column(Float, nullable=False)  # Particulate Matter 2.5 (ug/m3)
    co2 = Column(Float, nullable=False)   # Carbon Dioxide (ppm)
    temperature = Column(Float, nullable=False)  # Celsius
    humidity = Column(Float, nullable=False)     # Relative humidity (%)
    tvoc = Column(Float, nullable=False, default=0.1)  # Total Volatile Organic Compounds (mg/m3)
    co = Column(Float, nullable=False, default=0.0)    # Carbon Monoxide (ppm)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    is_simulated = Column(Boolean, default=True)
    scenario = Column(String(50), default="normal")

    # Relationships
    sensor = relationship("Sensor", back_populates="measurements")
    room = relationship("Room", back_populates="measurements")


class Equipment(Base):
    """Air quality remediation and climate equipment (purifier, humidifier, etc.)."""
    __tablename__ = "equipment"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)  # purifier, humidifier, dehumidifier, ventilation, ac
    status = Column(String(20), default="idle")     # running, idle, off, maintenance
    mode = Column(String(20), default="auto")       # auto, manual, eco, turbo
    last_maintenance = Column(DateTime, default=datetime.utcnow)

    # Relationships
    room = relationship("Room", back_populates="equipment")


class Conversation(Base):
    """Chat conversation history between user and SAQSHY AIR AI."""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), default="Air Quality Consultation")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """Individual chat message within a conversation."""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")


class Recommendation(Base):
    """Actionable recommendations derived from environmental rule engine."""
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    type = Column(String(50), nullable=False)       # ventilation, purification, humidity, temperature, safety
    severity = Column(String(20), nullable=False)   # info, warning, danger, critical
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    action = Column(String(255), nullable=True)     # immediate suggested action
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)

    # Relationships
    room = relationship("Room", back_populates="recommendations")


class Alert(Base):
    """Environmental hazards and safety alerts."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    type = Column(String(50), nullable=False)       # co_danger, pm25_spike, co2_high, mold_risk, etc.
    severity = Column(String(20), nullable=False)   # warning, danger, critical
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)

    # Relationships
    room = relationship("Room", back_populates="alerts")
