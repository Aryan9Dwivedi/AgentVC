from __future__ import annotations

import urllib.parse
from datetime import date, timedelta
from typing import Iterable

from agentvc_generator.connectors.base import SourceConnector
from agentvc_generator.connectors.http import fetch_json
from agentvc_generator.connectors.text_utils import clean_html
from agentvc_generator.entities import extract_entity_mentions, mentions_to_links
from agentvc_generator.models import RawSourceRecord, SourcePacket


class CrossrefQueryConnector(SourceConnector):
    source_id = "crossref"
    source_name = "Crossref"
    source_type = "paper"
    default_channel = "bioscience"
    query_prefix = ""
    crossref_filter = ""

    def fetch(self, query: str, limit: int, since_days: int = 7) -> Iterable[RawSourceRecord]:
        since = date.today() - timedelta(days=since_days)
        params = {
            "query": f"{self.query_prefix} {query}".strip(),
            "filter": ",".join(part for part in [f"from-pub-date:{since.isoformat()}", self.crossref_filter] if part),
            "rows": limit,
            "select": "DOI,title,abstract,author,published-print,published-online,published,URL,container-title,subtitle,publisher",
        }
        data = fetch_json("https://api.crossref.org/works", params)
        records: list[RawSourceRecord] = []
        for item in data.get("message", {}).get("items", []):
            doi = item.get("DOI", "")
            records.append(
                RawSourceRecord(
                    source_name=self.source_name,
                    source_type=self.source_type,
                    source_url=item.get("URL") or (f"https://doi.org/{doi}" if doi else ""),
                    external_id=doi or item.get("URL", ""),
                    payload=item,
                )
            )
        return records

    def normalize(self, record: RawSourceRecord, channel: str | None = None) -> SourcePacket:
        payload = record.payload
        title = " ".join(payload.get("title") or payload.get("subtitle") or []) or record.external_id
        abstract = clean_html(payload.get("abstract", ""))
        authors = [
            " ".join(part for part in [author.get("given"), author.get("family")] if part)
            for author in payload.get("author", [])
        ]
        date_parts = (
            payload.get("published-online", {}).get("date-parts")
            or payload.get("published-print", {}).get("date-parts")
            or payload.get("published", {}).get("date-parts")
            or []
        )
        published_at = "-".join(str(part) for part in date_parts[0]) if date_parts else None
        raw_text = "\n\n".join(part for part in [abstract, "Authors: " + ", ".join(authors)] if part.strip())
        mentions = extract_entity_mentions(f"{title}\n{raw_text}")
        return SourcePacket(
            channel=channel or self.default_channel,
            source_name=record.source_name,
            source_type=record.source_type,
            source_url=record.source_url,
            external_id=record.external_id,
            title=title,
            raw_text=raw_text,
            published_at=published_at,
            fetched_at=record.fetched_at,
            entities=mentions,
            links=mentions_to_links(mentions),
            provenance={
                "raw_checksum": record.checksum,
                "connector": self.source_id,
                "connector_version": "0.1.0",
                "publisher": payload.get("publisher"),
                "container_title": payload.get("container-title", []),
                "crossref_query_url": "https://api.crossref.org/works?"
                + urllib.parse.urlencode({"query": self.query_prefix}),
            },
        )


class SSRNConnector(CrossrefQueryConnector):
    source_id = "ssrn"
    source_name = "SSRN"
    source_type = "preprint"
    query_prefix = "SSRN"
    crossref_filter = "prefix:10.2139"


class ASCOConnector(CrossrefQueryConnector):
    source_id = "asco_annual_meeting"
    source_name = "ASCO Annual Meeting"
    source_type = "conference_abstract"
    query_prefix = "ASCO Annual Meeting abstract"


class AACRConnector(CrossrefQueryConnector):
    source_id = "aacr_annual_meeting"
    source_name = "AACR Annual Meeting"
    source_type = "conference_abstract"
    query_prefix = "AACR Annual Meeting abstract"


class AANConnector(CrossrefQueryConnector):
    source_id = "aan_annual_meeting"
    source_name = "AAN Annual Meeting"
    source_type = "conference_abstract"
    query_prefix = "AAN Annual Meeting abstract"

