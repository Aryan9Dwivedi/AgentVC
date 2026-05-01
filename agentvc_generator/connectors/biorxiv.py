from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

from agentvc_generator.connectors.base import SourceConnector
from agentvc_generator.connectors.http import fetch_json
from agentvc_generator.entities import extract_entity_mentions, mentions_to_links
from agentvc_generator.models import RawSourceRecord, SourcePacket


class BiorxivConnector(SourceConnector):
    source_id = "biorxiv"
    source_name = "bioRxiv"
    source_type = "preprint"
    default_channel = "bioscience"

    def fetch(self, query: str, limit: int, since_days: int = 7) -> Iterable[RawSourceRecord]:
        today = date.today()
        start = today - timedelta(days=since_days)
        data = fetch_json(
            f"https://api.biorxiv.org/details/biorxiv/{start.isoformat()}/{today.isoformat()}/0"
        )
        records: list[RawSourceRecord] = []
        query_lower = query.lower()
        for item in data.get("collection", []):
            haystack = f"{item.get('title', '')} {item.get('abstract', '')}".lower()
            if query_lower not in haystack:
                continue
            doi = item.get("doi") or item.get("server") or item.get("title", "")
            records.append(
                RawSourceRecord(
                    source_name=self.source_name,
                    source_type=self.source_type,
                    source_url=f"https://doi.org/{doi}" if doi else "",
                    external_id=doi,
                    payload=item,
                )
            )
            if len(records) >= limit:
                break
        return records

    def normalize(self, record: RawSourceRecord, channel: str | None = None) -> SourcePacket:
        payload = record.payload
        title = payload.get("title") or record.external_id
        raw_text = payload.get("abstract") or ""
        mentions = extract_entity_mentions(f"{title}\n{raw_text}")
        return SourcePacket(
            channel=channel or self.default_channel,
            source_name=record.source_name,
            source_type=record.source_type,
            source_url=record.source_url,
            external_id=record.external_id,
            title=title,
            raw_text=raw_text,
            published_at=payload.get("date"),
            fetched_at=record.fetched_at,
            entities=mentions,
            links=mentions_to_links(mentions),
            provenance={
                "raw_checksum": record.checksum,
                "connector": self.source_id,
                "connector_version": "0.1.0",
                "authors": payload.get("authors"),
                "affiliation": payload.get("author_corresponding_institution"),
                "category": payload.get("category"),
            },
        )
