"""Read-only MCP tool for the RoomBook free-slots API."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from typing_extensions import TypedDict

mcp = FastMCP("RoomBook")


class FreeSlotsResult(TypedDict):
    count: int
    slots: list[dict[str, int | str]]


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False))
def find_free_slots(
    date: str, duration_minutes: int, room_id: int | None = None,
) -> FreeSlotsResult:
    """Свободные интервалы RoomBook на дату YYYY-MM-DD.

    Длительность: 30–540 минут, кратна 30. Комната: 101–103 или все комнаты.
    Только поиск: бронирования не создаются и не изменяются.
    """
    params = {"date": date, "duration_minutes": duration_minutes}
    if room_id is not None:
        params["room_id"] = room_id
    api_url = os.environ.get("ROOMBOOK_API_URL", "http://127.0.0.1:8765")
    url = api_url.rstrip("/") + "/free-slots?" + urlencode(params)
    request = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=5) as response:
            slots = json.load(response)
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise ValueError(
            f"API RoomBook вернул HTTP {error.code}: {detail}"
        ) from error
    except (URLError, OSError) as error:
        raise ValueError(f"API RoomBook недоступен: {error}") from error
    except (ValueError, UnicodeError) as error:
        raise ValueError("API RoomBook вернул некорректный JSON") from error
    if not isinstance(slots, list) or any(
        not isinstance(slot, dict)
        or not {"room_id", "date", "start", "end"} <= slot.keys()
        for slot in slots
    ):
        raise ValueError("API RoomBook вернул некорректный список интервалов")
    return {"count": len(slots), "slots": slots}


if __name__ == "__main__":
    mcp.run(transport="stdio")
