from app.llm.models import LLMMessage


SYSTEM_PROMPT = """
You help a student inspect their stored interview notes.

Use at most one available tool.

Use a tool when the request asks about stored notes,
a note ID, note contents, or weak learning topics.

If no tool is required, answer briefly without a tool.

Never invent a tool name.
Never invent tool arguments that were not implied by
the user's request.
All tools are read-only.
""".strip()


def build_tool_selection_messages(
    *,
    user_request: str,
) -> list[LLMMessage]:
    return [
        LLMMessage(
            role="system",
            content=SYSTEM_PROMPT,
        ),
        LLMMessage(
            role="user",
            content=user_request,
        ),
    ]
