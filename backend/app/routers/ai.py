"""AI consultation and environmental root-cause analysis router."""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import Conversation, Measurement, Message, Room
from app.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationDetailResponse,
    ConversationResponse,
    MessageResponse,
    SourceAnalysisRequest,
    SourceAnalysisResponse,
    SourceHypothesis,
)
from app.services.ai_service import analyze_pollution_sources, get_ai_response
from app.services.simulator import calculate_aqi, generate_reading

router = APIRouter(prefix="/api/ai", tags=["AI"])


@router.post("/chat", response_model=ChatResponse)
def chat_with_ai(
    chat_in: ChatRequest,
    db: Session = Depends(get_db),
):
    """Chat with SAQSHY AIR AI assistant with optional real-time indoor sensor context."""
    user_msg_text = chat_in.message.strip()
    if not user_msg_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty",
        )

    # 1. Resolve or create Conversation
    conversation: Optional[Conversation] = None
    if chat_in.conversation_id:
        conversation = db.query(Conversation).filter(Conversation.id == chat_in.conversation_id).first()

    if not conversation:
        title_snippet = user_msg_text[:40] + ("..." if len(user_msg_text) > 40 else "")
        conversation = Conversation(title=title_snippet, created_at=datetime.utcnow())
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # 2. Extract conversation history for context
    past_messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.timestamp.asc())
        .all()
    )
    history_payload = [{"role": m.role, "content": m.content} for m in past_messages]

    # 3. Gather real-time sensor context if requested
    sensor_context = None
    if chat_in.include_sensor_context:
        # Find room with worst PM2.5 or first room
        latest_reading = db.query(Measurement).order_by(desc(Measurement.timestamp)).first()
        if latest_reading:
            room = db.query(Room).filter(Room.id == latest_reading.room_id).first()
            aqi, aqi_status = calculate_aqi(latest_reading.pm25)
            sensor_context = {
                "room_name": room.name if room else "Living Room",
                "room_type": room.type if room else "living_room",
                "pm25": latest_reading.pm25,
                "co2": latest_reading.co2,
                "temperature": latest_reading.temperature,
                "humidity": latest_reading.humidity,
                "tvoc": latest_reading.tvoc,
                "co": latest_reading.co,
                "aqi": aqi,
                "aqi_status": aqi_status,
            }
        else:
            sim = generate_reading(scenario="normal", step=0)
            sensor_context = {
                "room_name": "Living Room",
                "room_type": "living_room",
                "pm25": sim["pm25"],
                "co2": sim["co2"],
                "temperature": sim["temperature"],
                "humidity": sim["humidity"],
                "tvoc": sim["tvoc"],
                "co": sim["co"],
                "aqi": sim["aqi"],
                "aqi_status": sim["aqi_status"],
            }

    # 4. Generate AI response
    ai_reply_text = get_ai_response(
        user_message=user_msg_text,
        sensor_context=sensor_context,
        conversation_history=history_payload,
    )

    # 5. Persist user and assistant messages
    now = datetime.utcnow()
    user_db_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=user_msg_text,
        timestamp=now,
    )
    assistant_db_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=ai_reply_text,
        timestamp=now,
    )
    db.add(user_db_msg)
    db.add(assistant_db_msg)
    db.commit()

    return ChatResponse(
        response=ai_reply_text,
        conversation_id=conversation.id,
        context_used=sensor_context,
    )


@router.get("/conversations", response_model=List[ConversationResponse])
def list_conversations(db: Session = Depends(get_db)):
    """List all AI consultation conversations with message counts and latest preview."""
    conversations = db.query(Conversation).order_by(desc(Conversation.created_at)).all()
    results = []

    for c in conversations:
        count = db.query(Message).filter(Message.conversation_id == c.id).count()
        last_msg = (
            db.query(Message)
            .filter(Message.conversation_id == c.id)
            .order_by(desc(Message.timestamp))
            .first()
        )
        snippet = (last_msg.content[:80] + "...") if last_msg else None

        results.append(
            ConversationResponse(
                id=c.id,
                title=c.title,
                created_at=c.created_at,
                message_count=count,
                last_message=snippet,
            )
        )
    return results


@router.get("/conversations/{id}", response_model=ConversationDetailResponse)
def get_conversation_detail(id: int, db: Session = Depends(get_db)):
    """Retrieve full conversation transcript and ordered message history."""
    conv = db.query(Conversation).filter(Conversation.id == id).first()
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {id} not found",
        )

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == id)
        .order_by(Message.timestamp.asc())
        .all()
    )

    return ConversationDetailResponse(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        messages=[
            MessageResponse(
                id=m.id,
                conversation_id=m.conversation_id,
                role=m.role,
                content=m.content,
                timestamp=m.timestamp,
            )
            for m in messages
        ],
    )


@router.post("/analyze", response_model=SourceAnalysisResponse)
def trigger_source_analysis(
    request: Optional[SourceAnalysisRequest] = None,
    db: Session = Depends(get_db),
):
    """Trigger source of pollution diagnosis using environmental heuristics and telemetry."""
    room_id = request.room_id if request else None

    # Retrieve target room and its latest measurement
    room = None
    if room_id:
        room = db.query(Room).filter(Room.id == room_id).first()

    if not room:
        room = db.query(Room).first()

    room_name = room.name if room else "Living Room"
    resolved_room_id = room.id if room else 1

    latest = None
    if room:
        latest = (
            db.query(Measurement)
            .filter(Measurement.room_id == room.id)
            .order_by(desc(Measurement.timestamp))
            .first()
        )

    if latest:
        readings = {
            "pm25": latest.pm25,
            "co2": latest.co2,
            "temperature": latest.temperature,
            "humidity": latest.humidity,
            "tvoc": latest.tvoc,
            "co": latest.co,
        }
    else:
        # Fallback to simulated reading
        readings = generate_reading(scenario="cooking" if "kitchen" in room_name.lower() else "normal")

    analysis_dict = analyze_pollution_sources(readings=readings, room_name=room_name)

    hypotheses_objs = [
        SourceHypothesis(
            hypothesis=h["hypothesis"],
            likelihood=h["likelihood"],
            probability=h["probability"],
            reason=h["reason"],
        )
        for h in analysis_dict["hypotheses"]
    ]

    return SourceAnalysisResponse(
        room_id=resolved_room_id,
        room_name=room_name,
        hypotheses=hypotheses_objs,
        confidence=analysis_dict["confidence"],
        evidence=analysis_dict["evidence"],
        recommendations=analysis_dict["recommendations"],
        timestamp=datetime.utcnow(),
    )
