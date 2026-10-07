import re
from datetime import date as Date, time as Time
from typing import Literal

from pydantic import BaseModel, field_serializer, field_validator, model_validator

ROOM_IDS = (101, 102, 103)


def parse_date(value: str) -> Date:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("Date must use YYYY-MM-DD format")
    return Date.fromisoformat(value)


class Room(BaseModel):
    id: int
    name: str


class BookingInput(BaseModel):
    room_id: Literal[101, 102, 103]
    title: str
    date: Date
    start: Time
    end: Time

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("Title must not be empty")
        return title

    @field_validator("date", mode="before")
    @classmethod
    def validate_date(cls, value):
        if isinstance(value, Date):
            return value
        return parse_date(value)

    @field_validator("start", "end", mode="before")
    @classmethod
    def validate_time(cls, value):
        if isinstance(value, Time):
            return value
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]{2}:[0-9]{2}", value):
            raise ValueError("Time must use HH:MM format")
        return Time.fromisoformat(value)

    @model_validator(mode="after")
    def validate_interval(self):
        for value in (self.start, self.end):
            if value < Time(9) or value > Time(18):
                raise ValueError("Booking must be between 09:00 and 18:00")
            if value.minute % 30 or value.second or value.microsecond:
                raise ValueError("Time must use 30-minute increments")
        if self.start >= self.end:
            raise ValueError("Start must be earlier than end")
        return self

    @field_serializer("start", "end")
    def serialize_time(self, value: Time) -> str:
        return value.strftime("%H:%M")


class Booking(BookingInput):
    id: int
