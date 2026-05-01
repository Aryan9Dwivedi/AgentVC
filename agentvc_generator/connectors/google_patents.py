from __future__ import annotations

import json
import re
import urllib.parse
from datetime import date, timedelta
from typing import Iterable

from agentvc_generator.connectors.base import SourceConnector
from agentvc_generator.connectors.http import fetch_json, fetch_text
from agentvc_generator.connectors.text_utils import clean_html
from agentvc_generator.entities import extract_entity_mentions, mentions_to_links
from agentvc_generator.models import RawSourceRecord, SourcePacket


def meta_content(html_text: str, name: str) -> str:
    match = re.search(rf'<meta[^>]+name="{re.escape(name)}"[^>]+content="([^"]*)"', html_text)
    return clean_html(match.group(1)) if match else ""


def itemprop_values(html_text: str, prop: str) -> list[str]:
    values = re.findall(rf'itemprop="{re.escape(prop)}"[^>]*>(.*?)</', html_text, flags=re.S)
    return [clean_html(value) for value in values if clean_html(value)]


class GooglePatentsConnector(SourceConnector):
    source_id = "google_patents"
    source_name = "Google Patents"
    source_type = "patent"
    default_channel = "bioscience"

    def fetch(self, query: str, limit: int, since_days: int = 7) -> Iterable[RawSourceRecord]:
        since = date.today() - timedelta(days=since_days)
        patent_query = f"{query} after:publication:{since.strftime('%Y%m%d')}"
        url_param = urllib.parse.urlencode({"q": patent_query})
        data = fetch_json("https://patents.google.com/xhr/query", {"url": url_param, "exp": ""})
        records: list[RawSourceRecord] = []
        clusters = data.get("results", {}).get("cluster", [])
        for cluster in clusters:
            for result in cluster.get("result", []):
                if len(records) >= limit:
                    return records
                patent = result.get("patent", {})
                path = result.get("id", "")
                source_url = f"https://patents.google.com/{path}" if path else ""
                detail: dict[str, object] = {}
                try:
                    detail_html = fetch_text(source_url)
                    detail = {
                        "meta_description": meta_content(detail_html, "description"),
                        "dc_title": meta_content(detail_html, "DC.title"),
                        "inventors": itemprop_values(detail_html, "inventor"),
                        "assignees": itemprop_values(detail_html, "assigneeOriginal"),
                        "countries": itemprop_values(detail_html, "countryCode"),
                    }
                except Exception as error:
                    detail = {"detail_error": str(error)}
                payload = {
                    "search_result": patent,
                    "path": path,
                    "detail": detail,
                }
                external_id = path.removeprefix("patent/").removesuffix("/en") or result.get("id", "")
                records.append(
                    RawSourceRecord(
                        source_name=self.source_name,
                        source_type=self.source_type,
                        source_url=source_url,
                        external_id=external_id,
                        payload=payload,
                    )
                )
        return records

    def normalize(self, record: RawSourceRecord, channel: str | None = None) -> SourcePacket:
        search_result = record.payload.get("search_result", {})
        detail = record.payload.get("detail", {})
        title = clean_html(detail.get("dc_title") or search_result.get("title") or record.external_id)
        summary = clean_html(detail.get("meta_description") or search_result.get("snippet") or "")
        raw_text = "\n\n".join(
            part
            for part in [
                summary,
                "Inventors: " + ", ".join(detail.get("inventors", [])),
                "Assignees: " + ", ".join(detail.get("assignees", [])),
                "Countries: " + ", ".join(detail.get("countries", [])),
            ]
            if part.strip()
        )
        mentions = extract_entity_mentions(f"{title}\n{raw_text}")
        return SourcePacket(
            channel=channel or self.default_channel,
            source_name=record.source_name,
            source_type=record.source_type,
            source_url=record.source_url,
            external_id=record.external_id,
            title=title,
            raw_text=raw_text,
            published_at=None,
            fetched_at=record.fetched_at,
            entities=mentions,
            links=mentions_to_links(mentions),
            provenance={
                "raw_checksum": record.checksum,
                "connector": self.source_id,
                "connector_version": "0.1.0",
                "desired_fields_note": "Best-effort public Google Patents metadata; full claims/drawings may need a licensed patent data provider.",
                "payload_preview": json.dumps(record.payload)[:500],
            },
        )

