import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Response

from app import storage
from app.models import ROOM_IDS, Booking, BookingInput, Room, parse_date

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "roombook.sqlite3"


def create_app(database_path: str | Path | None = None) -> FastAPI:
    db_path = Path(database_path if database_path is not None else os.environ.get("ROOMBOOK_DB", DEFAULT_DB))
    application = FastAPI(title="RoomBook", version="0.1.0")

    @application.get("/rooms", response_model=list[Room])
    def get_rooms():
        return [{"id": room_id, "name": f"Комната {room_id}"} for room_id in ROOM_IDS]

    @application.post("/bookings", response_model=Booking, status_code=201)
    def create_booking(booking: BookingInput):
        data = booking.model_dump(mode="json")
        # Проверяем конфликт пересечения в той же комнате и дате
        conflict = storage.find_conflict(
            db_path, data["room_id"], data["date"], data["start"], data["end"]
        )
        if conflict is not None:
            # Возвращаем 409 с понятной причиной и ID конфликтующего бронирования
            raise HTTPException(
                status_code=409,
                detail={"reason": "overlap", "conflict_id": conflict["id"]},
            )
        return storage.add_booking(db_path, data)

    @application.get("/bookings", response_model=list[Booking])
    def get_bookings(date: str = Query(description="Дата в формате YYYY-MM-DD")):
        try:
            day = parse_date(date)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return storage.list_bookings(db_path, day.isoformat())

    @application.delete("/bookings/{booking_id}", status_code=204)
    def remove_booking(booking_id: int):
        if not storage.delete_booking(db_path, booking_id):
            raise HTTPException(status_code=404, detail="Booking not found")
        return Response(status_code=204)

    return application


app = create_app()
