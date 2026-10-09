from contextlib import contextmanager
from pathlib import Path
import sqlite3


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
            (
                "INSERT INTO bookings (room_id, title, date, start, end) "
                "VALUES (?, ?, ?, ?, ?)"
            ),
            (
                booking["room_id"],
                booking["title"],
                booking["date"],
                booking["start"],
                booking["end"],
            ),
        )
        return {**booking, "id": cursor.lastrowid}


def list_bookings(path: Path, date: str) -> list[dict]:
    with database(path) as connection:
        rows = connection.execute(
            "SELECT * FROM bookings WHERE date = ? ORDER BY room_id, start, id",
            (date,),
        ).fetchall()
        return [dict(row) for row in rows]


def find_conflict(
    path: Path, room_id: int, date: str, start: str, end: str
) -> dict | None:
    """Return conflicting booking for the same room/date or None.

    Интервалы считаются полуоткрытыми: [start, end). Пересечение:
    new_start < existing_end AND existing_start < new_end.
    """
    with database(path) as connection:
        row = connection.execute(
            """
            SELECT * FROM bookings
            WHERE room_id = ? AND date = ?
              AND ? < end AND start < ?
            ORDER BY id
            LIMIT 1
            """,
            (room_id, date, start, end),
        ).fetchone()
        return dict(row) if row else None


def delete_booking(path: Path, booking_id: int) -> bool:
    with database(path) as connection:
        cursor = connection.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
        return cursor.rowcount == 1


def list_free_slots(
    path: Path, date: str, duration_minutes: int, room_id: int | None
) -> list[dict]:
    """Return all free time intervals for the given date and optional room.

    Интервалы считаются полуоткрытыми: [start, end). Перебираем возможные
    старты с шагом 30 минут в пределах рабочего дня 09:00–18:00 и исключаем
    те, что пересекаются с существующими бронированиями той же комнаты и даты.
    Результат отсортирован по началу и комнате.
    """

    def to_minutes(hhmm: str) -> int:
        h, m = hhmm.split(":")
        return int(h) * 60 + int(m)

    def to_hhmm(minutes: int) -> str:
        h = minutes // 60
        m = minutes % 60
        return f"{h:02d}:{m:02d}"

    start_day = 9 * 60
    end_day = 18 * 60

    # Выбираем комнаты: одна указанная или все три
    rooms = [room_id] if room_id is not None else [101, 102, 103]

    # Загружаем расписание дня заранее и раскладываем по комнатам
    by_room: dict[int, list[tuple[int, int]]] = {r: [] for r in rooms}
    with database(path) as connection:
        rows = connection.execute(
            "SELECT room_id, start, end FROM bookings WHERE date = ?",
            (date,),
        ).fetchall()
        for row in rows:
            r = int(row["room_id"])
            if r in by_room:
                by_room[r].append((to_minutes(row["start"]), to_minutes(row["end"])) )

    # Для устойчивости проверок пересечений отсортируем интервалы по началу
    for r in by_room:
        by_room[r].sort(key=lambda p: (p[0], p[1]))

    result: list[dict] = []
    last_start = end_day - duration_minutes
    if last_start < start_day:
        # Длительность не помещается в рабочий день — вариантов нет
        return []

    # Перебираем кандидаты по началу, внутри — комнаты по возрастанию
    t = start_day
    while t <= last_start:
        candidate_end = t + duration_minutes
        for r in sorted(rooms):
            busy = False
            for (b_start, b_end) in by_room.get(r, []):
                # Пересечение: new_start < existing_end AND existing_start < new_end
                if t < b_end and b_start < candidate_end:
                    busy = True
                    break
            if not busy:
                result.append(
                    {
                        "room_id": r,
                        "date": date,
                        "start": to_hhmm(t),
                        "end": to_hhmm(candidate_end),
                    }
                )
        t += 30

    # Порядок уже по началу и комнате.
    return result
