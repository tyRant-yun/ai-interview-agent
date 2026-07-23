from pydantic import BaseModel

from app.api.sse import encode_sse


class ExamplePayload(BaseModel):
    text: str


def test_encode_sse_model():
    result = encode_sse(
        event="delta",
        data=ExamplePayload(
            text="hello"
        ),
    )

    assert result == (
        'event: delta\n'
        'data: {"text":"hello"}\n\n'
    )


def test_encode_sse_preserves_unicode():
    result = encode_sse(
        event="delta",
        data={
            "text": "你好",
        },
    )

    assert '"你好"' in result
    assert result.endswith("\n\n")
