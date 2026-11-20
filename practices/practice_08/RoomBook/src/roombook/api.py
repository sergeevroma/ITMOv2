from typing import Annotated

from fastapi import APIRouter, Query, Response

from roombook.catalog import ROOMS
from roombook.rules import CLOSES_AT, OPENS_AT, SLOT_MINUTES, TIMEZONE, to_minutes
from roombook.schemas import (
    Booking,
    BookingCreate,
    BookingRules,
    CalendarDate,
    ErrorResponse,
    FreeSlot,
    Room,
)
from roombook.service import BookingService

VALIDATION_RESPONSE = {422: {"model": ErrorResponse, "description": "Некорректные данные"}}
RoomFilter = Annotated[int | None, Query(gt=0)]
Duration = Annotated[
    int,
    Query(
        ge=SLOT_MINUTES, le=to_minutes(CLOSES_AT) - to_minutes(OPENS_AT), multiple_of=SLOT_MINUTES
    ),
]


def build_router(service: BookingService) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/rooms", response_model=list[Room], tags=["rooms"], operation_id="listRooms")
    def list_rooms():
        return ROOMS

    @router.get(
        "/booking-rules", response_model=BookingRules, tags=["rooms"], operation_id="getRules"
    )
    def booking_rules():
        return BookingRules(
            opens_at=OPENS_AT, closes_at=CLOSES_AT, slot_minutes=SLOT_MINUTES, timezone=TIMEZONE
        )

    @router.get(
        "/bookings",
        response_model=list[Booking],
        tags=["bookings"],
        responses=VALIDATION_RESPONSE,
        operation_id="listBookings",
    )
    def list_bookings(date: CalendarDate, room_id: RoomFilter = None):
        return service.list(date, room_id)

    @router.post(
        "/bookings",
        response_model=Booking,
        status_code=201,
        tags=["bookings"],
        operation_id="createBooking",
        responses=VALIDATION_RESPONSE
        | {409: {"model": ErrorResponse, "description": "Комната занята"}},
    )
    def create_booking(booking: BookingCreate):
        return service.create(booking)

    @router.delete(
        "/bookings/{booking_id}",
        status_code=204,
        tags=["bookings"],
        operation_id="cancelBooking",
        responses=VALIDATION_RESPONSE
        | {404: {"model": ErrorResponse, "description": "Бронирование не найдено"}},
    )
    def cancel_booking(booking_id: int):
        service.cancel(booking_id)
        return Response(status_code=204)

    @router.get(
        "/free-slots",
        response_model=list[FreeSlot],
        tags=["bookings"],
        responses=VALIDATION_RESPONSE,
        operation_id="findFreeSlots",
    )
    def free_slots(date: CalendarDate, duration_minutes: Duration, room_id: RoomFilter = None):
        return service.free_slots(date, duration_minutes, room_id)

    return router
