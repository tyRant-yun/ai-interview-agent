import json
from typing import Any

from pydantic import BaseModel


def encode_sse(
    *,
    event: str,
    data: BaseModel | dict[str, Any],
) -> str:
    """Encode one named Server-Sent Event."""

    if isinstance(data, BaseModel):
        payload = data.model_dump(
            mode="json"
        )
    else:
        payload = data

    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return (
        f"event: {event}\n"
        f"data: {serialized}\n\n"
    )
