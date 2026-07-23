class ToolError(Exception):
    """Base exception for tool infrastructure."""


class ToolProtocolError(ToolError):
    """Base error for invalid model-generated tool calls."""


class ToolNotRegisteredError(ToolProtocolError):
    """Raised when the model selects a non-registered tool."""


class ToolArgumentsError(ToolProtocolError):
    """Raised when generated tool arguments are invalid."""


class ToolSelectionError(ToolProtocolError):
    """Raised when a model selects an unsupported number of tools."""
