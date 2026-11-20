"""Ошибки приложения, не зависящие от HTTP."""


class RoomBookError(Exception):
    code: str

    def __init__(self, message: str, fields: dict[str, str] | None = None):
        super().__init__(message)
        self.message = message
        self.fields = fields or {}


class UnknownRoom(RoomBookError):
    code = "validation_error"

    def __init__(self):
        super().__init__(
            "Проверьте введённые данные.", {"room_id": "Выберите существующую комнату."}
        )


class BookingConflict(RoomBookError):
    code = "booking_conflict"

    def __init__(self):
        super().__init__("Комната уже занята в это время. Выберите другой интервал или комнату.")


class BookingNotFound(RoomBookError):
    code = "booking_not_found"

    def __init__(self):
        super().__init__("Бронирование не найдено. Обновите расписание.")
