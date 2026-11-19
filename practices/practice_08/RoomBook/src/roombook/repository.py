"""SQLite: отдельное соединение на операцию, транзакция на запись."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from roombook.errors import BookingConflict, BookingNotFound
from roombook.schemas import Booking, BookingCreate


class BookingRepository:
    def __init__(self, database_path: Path):
        self.database_path = database_path

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_id INTEGER NOT NULL,
                    organizer TEXT NOT NULL CHECK (length(trim(organizer)) BETWEEN 1 AND 80),
                    title TEXT NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 120),
                    date TEXT NOT NULL,
                    start TEXT NOT NULL,
                    end TEXT NOT NULL,
                    CHECK (start < end)
                );
                CREATE INDEX IF NOT EXISTS bookings_schedule ON bookings(date, room_id, start);
            """)

    def create(self, booking: BookingCreate) -> Booking:
        data = booking.model_dump(mode="json")
        with self._connection() as connection:
            # Захватываем блокировку до чтения: второй писатель проверит уже обновлённое расписание.
            connection.execute("BEGIN IMMEDIATE")
            conflict = connection.execute(
                """SELECT id FROM bookings
                   WHERE room_id = :room_id AND date = :date
                     AND :start < end AND start < :end LIMIT 1""",
                data,
            ).fetchone()
            if conflict is not None:
                raise BookingConflict()
            cursor = connection.execute(
                """INSERT INTO bookings (room_id, organizer, title, date, start, end)
                   VALUES (:room_id, :organizer, :title, :date, :start, :end)""",
                data,
            )
            return Booking.model_validate(data | {"id": cursor.lastrowid})

    def list(self, day: date, room_id: int | None = None) -> list[Booking]:
        query = "SELECT * FROM bookings WHERE date = ?"
        parameters: list[str | int] = [day.isoformat()]
        if room_id is not None:
            query += " AND room_id = ?"
            parameters.append(room_id)
        query += " ORDER BY room_id, start, id"
        with self._connection() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [Booking.model_validate(dict(row)) for row in rows]

    def delete(self, booking_id: int) -> None:
        with self._connection() as connection:
            cursor = connection.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
            if cursor.rowcount == 0:
                raise BookingNotFound()
