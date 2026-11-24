from datetime import date

from roombook.catalog import ROOMS
from roombook.errors import UnknownRoom
from roombook.repository import BookingRepository
from roombook.rules import CLOSES_AT, OPENS_AT, SLOT_MINUTES, from_minutes, overlaps, to_minutes
from roombook.schemas import Booking, BookingCreate, FreeSlot


class BookingService:
    def __init__(self, repository: BookingRepository):
        self.repository = repository
        self.rooms = {room.id: room for room in ROOMS}

    def require_room(self, room_id: int) -> None:
        if room_id not in self.rooms:
            raise UnknownRoom()

    def create(self, booking: BookingCreate) -> Booking:
        self.require_room(booking.room_id)
        return self.repository.create(booking)

    def list(self, day: date, room_id: int | None = None) -> list[Booking]:
        if room_id is not None:
            self.require_room(room_id)
        return self.repository.list(day, room_id)

    def cancel(self, booking_id: int) -> None:
        self.repository.delete(booking_id)

    def free_slots(self, day: date, duration_minutes: int, room_id: int | None) -> list[FreeSlot]:
        bookings = self.list(day, room_id)
        room_ids = [room_id] if room_id is not None else sorted(self.rooms)
        busy = {room: [b for b in bookings if b.room_id == room] for room in room_ids}
        slots = []
        last_start = to_minutes(CLOSES_AT) - duration_minutes
        for minute in range(to_minutes(OPENS_AT), last_start + 1, SLOT_MINUTES):
            start, end = from_minutes(minute), from_minutes(minute + duration_minutes)
            for room in room_ids:
                if not any(overlaps(start, end, b.start, b.end) for b in busy[room]):
                    slots.append(FreeSlot(room_id=room, date=day, start=start, end=end))
        return slots
