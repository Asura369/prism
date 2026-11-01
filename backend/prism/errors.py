from __future__ import annotations

from typing import Any


class PrismError(Exception):
    error_class = "PrismError"
    retryable = False

    def __init__(self, message: str, **context: Any):
        super().__init__(message)
        self.message = message
        self.context = context

    @property
    def stage(self) -> str | None:
        return getattr(self, "_stage", None)

    @stage.setter
    def stage(self, value: str | None) -> None:
        self._stage = value

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_class": self.error_class,
            "stage": self.stage,
            "message": self.message,
            "retryable": self.retryable,
            "context": self.context,
        }


class ConfigError(PrismError):
    error_class = "ConfigError"


class AdapterUnavailable(PrismError):
    error_class = "AdapterUnavailable"

    def __init__(self, adapter_name: str, message: str | None = None):
        super().__init__(message or f"Adapter unavailable: {adapter_name}", adapter_name=adapter_name)
        self.adapter_name = adapter_name


class RetryExhausted(PrismError):
    error_class = "RetryExhausted"

    def __init__(self, adapter_name: str, attempts: int):
        super().__init__(f"{adapter_name} failed after {attempts} attempts", adapter_name=adapter_name, attempts=attempts)


class PipelineError(PrismError):
    error_class = "PipelineError"

    def __init__(self, stage: str, message: str, **context: Any):
        super().__init__(message, **context)
        self.stage = stage


class SpecValidationError(PipelineError):
    error_class = "SpecValidationError"

    def __init__(self, message: str, payload: Any = None, stage: str = "spec"):
        super().__init__(stage, message, payload=payload)


class InsufficientSourcesError(PipelineError):
    error_class = "InsufficientSourcesError"

    def __init__(self, found: int, required: int, stage: str = "ingest"):
        super().__init__(stage, f"Insufficient sources: found {found}, required {required}", found=found, required=required)


class SlideRenderError(PipelineError):
    error_class = "SlideRenderError"

    def __init__(self, slide_index: int, cause: str, stage: str = "render"):
        super().__init__(stage, f"Slide {slide_index} failed: {cause}", slide_index=slide_index)


class SlideOverflowError(PipelineError):
    error_class = "SlideOverflowError"

    def __init__(self, slide_index: int, field_name: str, stage: str = "render"):
        super().__init__(stage, f"Slide {slide_index} text overflow in {field_name}", slide_index=slide_index, field=field_name)


class PolicyViolation(PipelineError):
    error_class = "PolicyViolation"

    def __init__(self, reasons: list[str], stage: str = "policy"):
        super().__init__(stage, "Policy violation: " + "; ".join(reasons), reasons=reasons)


class ValidationError(PipelineError):
    error_class = "ValidationError"

    def __init__(self, reasons: list[str], stage: str = "validate"):
        super().__init__(stage, "Validation failed: " + "; ".join(reasons), reasons=reasons)


class DiscoveryError(PrismError):
    error_class = "DiscoveryError"


class InvalidTrendsCSV(DiscoveryError):
    error_class = "InvalidTrendsCSV"


class AngleGenerationError(DiscoveryError):
    error_class = "AngleGenerationError"


class JobCancelled(PrismError):
    error_class = "JobCancelled"


class JobNotFound(PrismError):
    error_class = "JobNotFound"

    def __init__(self, job_id: str):
        super().__init__(f"Job not found: {job_id}", job_id=job_id)
