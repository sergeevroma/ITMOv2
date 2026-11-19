import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from roombook.api import build_router
from roombook.errors import BookingConflict, BookingNotFound, RoomBookError, UnknownRoom
from roombook.repository import BookingRepository
from roombook.schemas import ApiError, ErrorResponse
from roombook.service import BookingService

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def error_response(status: int, code: str, message: str, fields: dict[str, str]) -> JSONResponse:
    body = ErrorResponse(error=ApiError(code=code, message=message, fields=fields))
    return JSONResponse(status_code=status, content=body.model_dump())


def validation_message(error: dict) -> str:
    messages = {
        "missing": "Обязательное поле.",
        "string_type": "Введите текст.",
        "string_too_short": "Поле не должно быть пустым.",
        "int_type": "Укажите целое число.",
        "int_parsing": "Укажите целое число.",
        "extra_forbidden": "Неизвестное поле.",
        "json_invalid": "Некорректный JSON.",
    }
    if error["type"] == "string_too_long":
        return f"Не более {error['ctx']['max_length']} символов."
    if error["type"] == "greater_than":
        return f"Значение должно быть больше {error['ctx']['gt']}."
    if error["type"] == "greater_than_equal":
        return f"Значение должно быть не меньше {error['ctx']['ge']}."
    if error["type"] == "less_than_equal":
        return f"Значение должно быть не больше {error['ctx']['le']}."
    if error["type"] == "multiple_of":
        return f"Значение должно быть кратно {error['ctx']['multiple_of']}."
    return messages.get(error["type"], error["msg"].removeprefix("Value error, "))


def create_app(
    database_path: str | Path | None = None,
    frontend_dir: str | Path | None = None,
) -> FastAPI:
    path = (
        database_path
        if database_path is not None
        else os.getenv("ROOMBOOK_DB", str(PROJECT_ROOT / "data" / "roombook.sqlite3"))
    )
    repository = BookingRepository(Path(path))
    service = BookingService(repository)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        repository.initialize()
        yield

    application = FastAPI(
        title="RoomBook",
        version="0.1.0",
        lifespan=lifespan,
        description="Бронирование учебных комнат и поиск свободных интервалов.",
    )

    @application.exception_handler(RoomBookError)
    async def domain_error(_request: Request, error: RoomBookError):
        statuses = {UnknownRoom: 422, BookingConflict: 409, BookingNotFound: 404}
        return error_response(statuses[type(error)], error.code, error.message, error.fields)

    @application.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, error: RequestValidationError):
        fields = {}
        for item in error.errors():
            location = [str(part) for part in item["loc"] if part not in {"body", "query", "path"}]
            field = "_form" if item["type"] == "json_invalid" else ".".join(location) or "_form"
            fields.setdefault(field, validation_message(item))
        return error_response(422, "validation_error", "Проверьте введённые данные.", fields)

    application.include_router(build_router(service))
    # Фронтенд появится после макета. Его можно будет запускать с API на одном адресе.
    frontend = Path(frontend_dir) if frontend_dir is not None else PROJECT_ROOT / "frontend"
    if frontend_dir is not None or frontend.is_dir():
        application.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return application
