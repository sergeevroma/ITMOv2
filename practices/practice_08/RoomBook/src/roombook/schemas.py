"""Структуры запросов и ответов; ограничения форм отражаются в OpenAPI."""

from datetime import date, time
from typing import Annotated

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
    ValidationInfo,
    WithJsonSchema,
    field_validator,
)

from roombook.rules import CLOSES_AT, OPENS_AT, SLOT_MINUTES, parse_date, parse_time

CalendarDate = Annotated[date, BeforeValidator(parse_date)]
ClockTime = Annotated[
    time,
    BeforeValidator(parse_time),
    PlainSerializer(lambda value: value.strftime("%H:%M"), return_type=str),
    WithJsonSchema({"type": "string", "pattern": "^[0-9]{2}:[0-9]{2}$", "examples": ["10:00"]}),
]


class Room(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    capacity: int
    equipment: tuple[str, ...]


class BookingFields(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    room_id: int = Field(strict=True, gt=0)
    organizer: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=120)
    date: CalendarDate
    start: ClockTime
    end: ClockTime


class BookingCreate(BookingFields):
    @field_validator("start", "end")
    @classmethod
    def validate_working_time(cls, value: time) -> time:
        if not OPENS_AT <= value <= CLOSES_AT:
            raise ValueError("Комнаты доступны с 09:00 до 18:00.")
        if value.minute % SLOT_MINUTES or value.second or value.microsecond:
            raise ValueError("Время должно быть кратно 30 минутам.")
        return value

    @field_validator("end")
    @classmethod
    def validate_interval(cls, value: time, info: ValidationInfo) -> time:
        start = info.data.get("start")
        if start is not None and value <= start:
            raise ValueError("Окончание должно быть позже начала.")
        return value


class Booking(BookingFields):
    id: int


class FreeSlot(BaseModel):
    room_id: int
    date: CalendarDate
    start: ClockTime
    end: ClockTime


class BookingRules(BaseModel):
    opens_at: ClockTime
    closes_at: ClockTime
    slot_minutes: int
    timezone: str


class ApiError(BaseModel):
    code: str
    message: str
    fields: dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ApiError
