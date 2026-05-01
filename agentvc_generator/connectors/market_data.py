from __future__ import annotations

from typing import Iterable

from agentvc_generator.connectors.base import SourceConnector
from agentvc_generator.connectors.http import fetch_json
from agentvc_generator.entities import extract_entity_mentions, mentions_to_links
from agentvc_generator.models import RawSourceRecord, SourcePacket


class YahooFinanceConnector(SourceConnector):
    source_id = "yahoo_finance"
    source_name = "Yahoo Finance"
    source_type = "market_quote"
    default_channel = "market_background"

    def fetch(self, query: str, limit: int, since_days: int = 7) -> Iterable[RawSourceRecord]:
        symbols = [item.strip().upper() for item in query.replace(";", ",").split(",") if item.strip()]
        symbols = symbols[:limit]
        if not symbols:
            return []
        records: list[RawSourceRecord] = []
        for symbol in symbols:
            data = fetch_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}")
            result = (data.get("chart", {}).get("result") or [{}])[0]
            meta = result.get("meta", {})
            quote = (result.get("indicators", {}).get("quote") or [{}])[0]
            payload = {
                "symbol": symbol,
                "meta": meta,
                "latest_quote": {key: values[-1] for key, values in quote.items() if values},
            }
            records.append(
                RawSourceRecord(
                    source_name=self.source_name,
                    source_type=self.source_type,
                    source_url=f"https://finance.yahoo.com/quote/{symbol}",
                    external_id=symbol,
                    payload=quote,
                )
            )
        return records

    def normalize(self, record: RawSourceRecord, channel: str | None = None) -> SourcePacket:
        payload = record.payload
        meta = payload.get("meta", {})
        latest = payload.get("latest_quote", {})
        title = f"{payload.get('symbol')} - {meta.get('longName') or meta.get('shortName') or 'Market quote'}"
        raw_text = "\n".join(
            [
                f"Price: {meta.get('regularMarketPrice')}",
                f"Previous close: {meta.get('previousClose')}",
                f"Chart close: {latest.get('close')}",
                f"Volume: {latest.get('volume')}",
                f"Exchange: {meta.get('exchangeName')}",
                f"Instrument type: {meta.get('instrumentType')}",
            ]
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
                "access_note": "Best-effort public quote endpoint; replace with licensed market data for production.",
            },
        )
