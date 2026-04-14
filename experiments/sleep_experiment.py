import time

from pydantic import Field
from scythe.base import ExperimentInputSpec, ExperimentOutputSpec
from scythe.registry import ExperimentRegistry


class SleepInput(ExperimentInputSpec):
    """A minimal experiment input with a configurable sleep duration."""

    sleep_duration: float = Field(
        default=0.0, description="Sleep duration in seconds", ge=0
    )


class SleepOutput(ExperimentOutputSpec):
    """Output recording the actual elapsed time of the sleep."""

    elapsed: float = Field(
        default=..., description="Actual elapsed time in seconds", ge=0
    )


@ExperimentRegistry.Register()
def sleep_task(input_spec: SleepInput) -> SleepOutput:
    """A no-op experiment that sleeps for a configurable duration."""
    start = time.monotonic()
    time.sleep(input_spec.sleep_duration)
    elapsed = time.monotonic() - start
    return SleepOutput(elapsed=elapsed)
