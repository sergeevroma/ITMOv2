import sqlite3
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def database(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    date TEXT NOT NULL,
                    start TEXT NOT NULL,
                    end TEXT NOT NULL
                )
                """
            )
            yield connection
    finally:
        connection.close()


def add_booking(path: Path, booking: dict) -> dict:
    with database(path) as connection:
        cursor = connection.execute(
            "INSERT INTO bookings (room_id, title, date, start, end) VALUES (?, ?, ?, ?, ?)",
            (booking["room_id"], booking["title"], booking["date"], booking["start"], booking["end"]),
        )
        return {**booking, "id": cursor.lastrowid}


def list_bookings(path: Path, date: str) -> list[dict]:
    with database(path) as connection:
        rows = connection.execute(
            "SELECT * FROM bookings WHERE date = ? ORDER BY room_id, start, id",
            (date,),
        ).fetchall()
        return [dict(row) for row in rows]


def delete_booking(path: Path, booking_id: int) -> bool:
    with database(path) as connection:
        cursor = connection.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
        return cursor.rowcount == 1
