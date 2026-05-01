from __future__ import annotations

from typing import Iterable

from agentvc_generator.connectors.base import SourceConnector
from agentvc_generator.connectors.http import fetch_json
from agentvc_generator.entities import extract_entity_mentions, mentions_to_links
from agentvc_generator.models import RawSourceRecord, SourcePacket


def cik_string(cik: int | str) -> str:
    return str(cik).zfill(10)


class SECEdgarConnector(SourceConnector):
    source_id = "sec_edgar"
    source_name = "SEC EDGAR"
    source_type = "financial_filing"
    default_channel = "financial_fiscal"

    def fetch(self, query: str, limit: int, since_days: int = 7) -> Iterable[RawSourceRecord]:
        ticker_map = fetch_json("https://www.sec.gov/files/company_tickers.json")
        requested = {item.strip().upper() for item in query.replace(";", ",").split(",") if item.strip()}
        matches = []
        for item in ticker_map.values():
            ticker = item.get("ticker", "").upper()
            title = item.get("title", "")
            if ticker in requested or any(term.lower() in title.lower() for term in requested):
                matches.append(item)
            if len(matches) >= limit:
                break

        records: list[RawSourceRecord] = []
        for item in matches:
            cik = cik_string(item["cik_str"])
            facts = fetch_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json")
            payload = {
                "ticker": item.get("ticker"),
                "company": item.get("title"),
                "cik": cik,
                "facts": facts,
            }
            records.append(
                RawSourceRecord(
                    source_name=self.source_name,
                    source_type=self.source_type,
                    source_url=f"https://www.sec.gov/edgar/browse/?CIK={cik}",
                    external_id=cik,
                    payload=payload,
                )
            )
        return records

    def normalize(self, record: RawSourceRecord, channel: str | None = None) -> SourcePacket:
        payload = record.payload
        facts = payload.get("facts", {}).get("facts", {}).get("us-gaap", {})
        selected = []
        for key in ["Revenues", "Assets", "Liabilities", "NetIncomeLoss", "ResearchAndDevelopmentExpense"]:
            fact = facts.get(key, {})
            units = fact.get("units", {})
            values = next(iter(units.values()), [])
            latest = values[-1] if values else {}
            if latest:
                selected.append(f"{key}: {latest.get('val')} ({latest.get('fy')} {latest.get('fp')})")
        title = f"{payload.get('ticker')} - {payload.get('company')} SEC financial facts"
        raw_text = "\n".join(selected) or "SEC company facts record fetched; no selected US-GAAP fields found."
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
                "ticker": payload.get("ticker"),
                "cik": payload.get("cik"),
                "access_note": "SEC company facts endpoint; query should be ticker symbols or company names.",
            },
        )

