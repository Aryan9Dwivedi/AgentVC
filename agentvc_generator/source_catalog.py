from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_CATALOG_PATH = Path("config/sources.json")


class SourceCatalog:
    def __init__(self, path: Path = DEFAULT_CATALOG_PATH):
        self.path = path
        self.data = json.loads(path.read_text(encoding="utf-8"))

    def channels(self) -> list[dict[str, Any]]:
        return self.data.get("channels", [])

    def sources(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for channel in self.channels():
            for source in channel.get("sources", []):
                source_with_channel = dict(source)
                source_with_channel["channel"] = channel["id"]
                source_with_channel["channel_name"] = channel["name"]
                results.append(source_with_channel)
        return results

    def find_source(self, source_id: str, channel: str | None = None) -> dict[str, Any] | None:
        for source in self.sources():
            if source["id"] == source_id and (channel is None or source["channel"] == channel):
                return source
        return None

