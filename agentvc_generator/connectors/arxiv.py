from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Iterable

from agentvc_generator.connectors.base import SourceConnector
from agentvc_generator.connectors.http import fetch_xml
from agentvc_generator.entities import extract_entity_mentions, mentions_to_links
from agentvc_generator.models import RawSourceRecord, SourcePacket


ATOM = "{http://www.w3.org/2005/Atom}"


class ArxivConnector(SourceConnector):
    source_id = "arxiv"
    source_name = "arXiv"
    source_type = "preprint"
    default_channel = "bioscience"

    def fetch(self, query: str, limit: int, since_days: int = 7) -> Iterable[RawSourceRecord]:
        since = datetime.combine(date.today() - timedelta(days=since_days), datetime.min.time(), tzinfo=timezone.utc)
        root = fetch_xml(
            "https://export.arxiv.org/api/query",
            {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": limit,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            },
        )
        records: list[RawSourceRecord] = []
        for entry in root.findall(f"{ATOM}entry"):
            published = entry.findtext(f"{ATOM}published")
            if published:
                try:
                    parsed = datetime.fromisoformat(published.replace("Z", "+00:00"))
                    if parsed < since:
                        continue
                except ValueError:
                    pass
            url = entry.findtext(f"{ATOM}id") or ""
            external_id = url.rsplit("/", 1)[-1]
            payload = {
                "id": external_id,
                "url": url,
                "title": " ".join((entry.findtext(f"{ATOM}title") or "").split()),
                "abstract": " ".join((entry.findtext(f"{ATOM}summary") or "").split()),
                "published": published,
                "updated": entry.findtext(f"{ATOM}updated"),
                "authors": [
                    author.findtext(f"{ATOM}name")
                    for author in entry.findall(f"{ATOM}author")
                    if author.findtext(f"{ATOM}name")
                ],
            }
            records.append(
                RawSourceRecord(
                    source_name=self.source_name,
                    source_type=self.source_type,
                    source_url=url,
                    external_id=external_id,
                    payload=payload,
                )
            )
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
            published_at=payload.get("published"),
            fetched_at=record.fetched_at,
            entities=mentions,
            links=mentions_to_links(mentions),
            provenance={
                "raw_checksum": record.checksum,
                "connector": self.source_id,
                "connector_version": "0.1.0",
                "authors": payload.get("authors", []),
            },
        )
