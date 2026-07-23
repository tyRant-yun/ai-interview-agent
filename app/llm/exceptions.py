class LLMError(Exception):
    """Base exception for model-access errors."""


class LLMNotConfiguredError(LLMError):
    """Raised when required model configuration is missing."""


class LLMTimeoutError(LLMError):
    """Raised when the upstream model request times out."""


class LLMUpstreamError(LLMError):
    """Raised when the upstream model service returns an error."""


class LLMInvalidResponseError(LLMError):
    """Raised when the model response cannot satisfy our contract."""
