from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Iterable

from agentvc_generator.connectors.base import SourceConnector
from agentvc_generator.connectors.http import fetch_text
from agentvc_generator.connectors.text_utils import clean_html
from agentvc_generator.entities import extract_entity_mentions, mentions_to_links
from agentvc_generator.models import RawSourceRecord, SourcePacket


def extract_label(html_text: str, label: str) -> str:
    pattern = rf"{re.escape(label)}\s*:?\s*</td>\s*<td[^>]*>\s*(.*?)\s*</td>"
    match = re.search(pattern, html_text, flags=re.I | re.S)
    return clean_html(match.group(1)) if match else ""


class ICTRPConnector(SourceConnector):
    source_id = "ictrp"
    source_name = "International Clinical Trials Registry Platform"
    source_type = "trial"
    default_channel = "scientific_risk"

    def fetch(self, query: str, limit: int, since_days: int = 7) -> Iterable[RawSourceRecord]:
        search_html = fetch_text("https://trialsearch.who.int/", {"query": query})
        trial_ids = []
        for match in re.finditer(r"Trial2\.aspx\?TrialID=([^\"']+)", search_html):
            trial_id = clean_html(match.group(1))
            if trial_id and trial_id not in trial_ids:
                trial_ids.append(trial_id)
            if len(trial_ids) >= limit:
                break

        since = datetime.combine(date.today() - timedelta(days=since_days), datetime.min.time())
        records: list[RawSourceRecord] = []
        for trial_id in trial_ids:
            url = f"https://trialsearch.who.int/Trial2.aspx?TrialID={trial_id}"
            detail_html = fetch_text(url)
            payload = {
                "main_id": extract_label(detail_html, "Main ID"),
                "date_of_registration": extract_label(detail_html, "Date of registration"),
                "public_title": extract_label(detail_html, "Public title"),
                "scientific_title": extract_label(detail_html, "Scientific title"),
                "primary_sponsor": extract_label(detail_html, "Primary sponsor"),
                "health_condition": extract_label(detail_html, "Health condition(s) or problem(s) studied"),
                "intervention": extract_label(detail_html, "Intervention(s)"),
                "primary_outcome": extract_label(detail_html, "Primary outcome(s)"),
                "inclusion_criteria": extract_label(detail_html, "Inclusion criteria"),
                "exclusion_criteria": extract_label(detail_html, "Exclusion criteria"),
            }
            registration_date = payload.get("date_of_registration", "")
            parsed_registration = None
            for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%B %Y"]:
                try:
                    parsed_registration = datetime.strptime(registration_date, fmt)
                    break
                except ValueError:
                    continue
            if parsed_registration and parsed_registration < since:
                continue
            records.append(
                RawSourceRecord(
                    source_name=self.source_name,
                    source_type=self.source_type,
                    source_url=url,
                    external_id=payload.get("main_id") or trial_id,
                    payload=payload,
                )
            )
        return records

    def normalize(self, record: RawSourceRecord, channel: str | None = None) -> SourcePacket:
        payload = record.payload
        title = payload.get("public_title") or payload.get("scientific_title") or record.external_id
        raw_text = "\n\n".join(
            part
            for part in [
                "Sponsor: " + payload.get("primary_sponsor", ""),
                "Condition: " + payload.get("health_condition", ""),
                "Intervention: " + payload.get("intervention", ""),
                "Primary outcome: " + payload.get("primary_outcome", ""),
                "Inclusion criteria: " + payload.get("inclusion_criteria", ""),
                "Exclusion criteria: " + payload.get("exclusion_criteria", ""),
            ]
            if part.strip() and not part.endswith(": ")
        )
        mentions = extract_entity_mentions(f"{record.external_id}\n{title}\n{raw_text}")
        return SourcePacket(
            channel=channel or self.default_channel,
            source_name=record.source_name,
            source_type=record.source_type,
            source_url=record.source_url,
            external_id=record.external_id,
            title=title,
            raw_text=raw_text,
            published_at=payload.get("date_of_registration"),
            fetched_at=record.fetched_at,
            entities=mentions,
            links=mentions_to_links(mentions),
            provenance={
                "raw_checksum": record.checksum,
                "connector": self.source_id,
                "connector_version": "0.1.0",
                "access_note": "Public ICTRP search portal parser. Official XML web service may require WHO arrangement/cost recovery.",
            },
        )

