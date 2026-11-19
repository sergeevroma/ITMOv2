"""Общие правила времени и форматов."""

import re
from datetime import date, time

OPENS_AT = time(9)
CLOSES_AT = time(18)
SLOT_MINUTES = 30
TIMEZONE = "Europe/Moscow"


def parse_date(value: object) -> date:
    if type(value) is date:
        return value
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("Укажите дату в формате ГГГГ-ММ-ДД.")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("Укажите существующую дату.") from error


def parse_time(value: object) -> time:
    if isinstance(value, time) and value.tzinfo is None:
        return value
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{2}:[0-9]{2}", value):
        raise ValueError("Укажите время в формате ЧЧ:ММ.")
    try:
        return time.fromisoformat(value)
    except ValueError as error:
        raise ValueError("Укажите существующее время.") from error


def to_minutes(value: time) -> int:
    return value.hour * 60 + value.minute


def from_minutes(value: int) -> time:
    return time(value // 60, value % 60)


def overlaps(start: time, end: time, other_start: time, other_end: time) -> bool:
    return start < other_end and other_start < end
