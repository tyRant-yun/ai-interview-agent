class AgentExecutionError(Exception):
    """Base error for controlled Agent execution."""

    error_code = "agent_execution_error"


class AgentMaxStepsExceededError(
    AgentExecutionError
):
    """Raised when the Agent cannot finish in time."""

    error_code = "agent_max_steps_exceeded"


class AgentRepeatedToolCallError(
    AgentExecutionError
):
    """Raised when an identical call is repeated."""

    error_code = "agent_repeated_tool_call"
