from __future__ import annotations

import os
import re
from typing import Iterable

from agentvc_generator.connectors.base import SourceConnector
from agentvc_generator.connectors.http import fetch_json
from agentvc_generator.models import RawSourceRecord, SourcePacket


class UnpaywallConnector(SourceConnector):
    source_id = "unpaywall"
    source_name = "Unpaywall"
    source_type = "open_access_helper"
    default_channel = "bioscience"

    def fetch(self, query: str, limit: int, since_days: int = 7) -> Iterable[RawSourceRecord]:
        email = os.getenv("AGENTVC_TOOL_EMAIL", "agentvc@example.com")
        dois = re.findall(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", query, flags=re.I)
        records: list[RawSourceRecord] = []
        for doi in dois[:limit]:
            data = fetch_json(f"https://api.unpaywall.org/v2/{doi}", {"email": email})
            records.append(
                RawSourceRecord(
                    source_name=self.source_name,
                    source_type=self.source_type,
                    source_url=data.get("doi_url") or f"https://doi.org/{doi}",
                    external_id=doi,
                    payload=data,
                )
            )
        return records

    def normalize(self, record: RawSourceRecord, channel: str | None = None) -> SourcePacket:
        payload = record.payload
        best = payload.get("best_oa_location") or {}
        return SourcePacket(
            channel=channel or self.default_channel,
            source_name=record.source_name,
            source_type=record.source_type,
            source_url=record.source_url,
            external_id=record.external_id,
            title=payload.get("title") or record.external_id,
            raw_text=f"OA status: {payload.get('oa_status')}\nBest OA URL: {best.get('url_for_pdf') or best.get('url') or ''}",
            published_at=None,
            fetched_at=record.fetched_at,
            provenance={
                "raw_checksum": record.checksum,
                "connector": self.source_id,
                "connector_version": "0.1.0",
                "legal_note": "Open-access discovery only; does not bypass paywalls.",
            },
        )

