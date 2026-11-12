"""CRUD router for indoor rooms and zones."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Room, Sensor
from app.schemas import RoomCreate, RoomResponse, RoomUpdate

router = APIRouter(prefix="/api/rooms", tags=["Rooms"])


@router.get("/", response_model=List[RoomResponse])
def list_rooms(db: Session = Depends(get_db)):
    """List all rooms with sensor counts."""
    rooms = db.query(Room).all()
    results = []
    for r in rooms:
        count = db.query(Sensor).filter(Sensor.room_id == r.id).count()
        results.append(
            RoomResponse(
                id=r.id,
                name=r.name,
                type=r.type,
                floor=r.floor,
                created_at=r.created_at,
                sensors_count=count,
            )
        )
    return results


@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(room_in: RoomCreate, db: Session = Depends(get_db)):
    """Create a new room or monitored indoor zone."""
    room = Room(
        name=room_in.name,
        type=room_in.type,
        floor=room_in.floor,
    )
    db.add(room)
    db.commit()
    db.refresh(room)

    return RoomResponse(
        id=room.id,
        name=room.name,
        type=room.type,
        floor=room.floor,
        created_at=room.created_at,
        sensors_count=0,
    )


@router.get("/{id}", response_model=RoomResponse)
def get_room(id: int, db: Session = Depends(get_db)):
    """Retrieve details of a single room by ID."""
    room = db.query(Room).filter(Room.id == id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with id {id} not found",
        )
    count = db.query(Sensor).filter(Sensor.room_id == room.id).count()
    return RoomResponse(
        id=room.id,
        name=room.name,
        type=room.type,
        floor=room.floor,
        created_at=room.created_at,
        sensors_count=count,
    )


@router.put("/{id}", response_model=RoomResponse)
def update_room(id: int, room_in: RoomUpdate, db: Session = Depends(get_db)):
    """Update room properties (name, type, floor)."""
    room = db.query(Room).filter(Room.id == id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with id {id} not found",
        )

    if room_in.name is not None:
        room.name = room_in.name
    if room_in.type is not None:
        room.type = room_in.type
    if room_in.floor is not None:
        room.floor = room_in.floor

    db.commit()
    db.refresh(room)

    count = db.query(Sensor).filter(Sensor.room_id == room.id).count()
    return RoomResponse(
        id=room.id,
        name=room.name,
        type=room.type,
        floor=room.floor,
        created_at=room.created_at,
        sensors_count=count,
    )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(id: int, db: Session = Depends(get_db)):
    """Delete a room and cascade associated records."""
    room = db.query(Room).filter(Room.id == id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with id {id} not found",
        )
    db.delete(room)
    db.commit()
    return None
