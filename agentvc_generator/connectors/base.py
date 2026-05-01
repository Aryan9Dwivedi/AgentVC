from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from agentvc_generator.models import RawSourceRecord, SourcePacket


class SourceConnector(ABC):
    source_id: str
    source_name: str
    source_type: str
    default_channel: str

    @abstractmethod
    def fetch(self, query: str, limit: int, since_days: int = 7) -> Iterable[RawSourceRecord]:
        raise NotImplementedError

    @abstractmethod
    def normalize(self, record: RawSourceRecord, channel: str | None = None) -> SourcePacket:
        raise NotImplementedError
