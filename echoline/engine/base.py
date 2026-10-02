from dataclasses import dataclass
from typing import Protocol, Union

import numpy as np

SAMPLE_RATE = 16000


@dataclass(frozen=True)
class Partial:
    """Text of an utterance that is still being spoken; may change."""
    utterance_id: int
    text: str


@dataclass(frozen=True)
class Final:
    """Settled text of a finished utterance."""
    utterance_id: int
    text: str


Event = Union[Partial, Final]


class SpeechEngine(Protocol):
    def feed(self, samples: np.ndarray) -> list[Event]:
        """Consume 16 kHz mono float32 samples, return any new events."""

    def flush(self) -> list[Final]:
        """Finish pending audio, returning the last finals."""
