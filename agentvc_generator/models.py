from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: Any) -> str:
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True, default=str)
    return sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EntityMention:
    text: str
    entity_type: str = "unknown"
    source_field: str = "raw_text"
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GraphLink:
    target: str
    relationship: str
    target_type: str = "entity"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RawSourceRecord:
    source_name: str
    source_type: str
    source_url: str
    external_id: str
    payload: dict[str, Any]
    fetched_at: str = field(default_factory=utc_now_iso)

    @property
    def checksum(self) -> str:
        return stable_hash(self.payload)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["checksum"] = self.checksum
        return data


@dataclass(frozen=True)
class SourcePacket:
    channel: str
    source_name: str
    source_type: str
    source_url: str
    external_id: str
    title: str
    raw_text: str
    published_at: str | None
    fetched_at: str
    entities: list[EntityMention] = field(default_factory=list)
    links: list[GraphLink] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def packet_id(self) -> str:
        return stable_hash(f"{self.source_name}:{self.external_id}:{self.title}")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["packet_id"] = self.packet_id
        data["entities"] = [entity.to_dict() for entity in self.entities]
        data["links"] = [link.to_dict() for link in self.links]
        return data
