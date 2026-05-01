from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import Iterable
from xml.etree import ElementTree

from agentvc_generator.connectors.base import SourceConnector
from agentvc_generator.connectors.http import fetch_xml
from agentvc_generator.connectors.text_utils import clean_html, parse_datetime
from agentvc_generator.entities import extract_entity_mentions, mentions_to_links
from agentvc_generator.models import RawSourceRecord, SourcePacket


class FeedConnector(SourceConnector):
    source_id = "feed"
    source_name = "Feed"
    source_type = "article"
    default_channel = "bioscience"
    env_var = ""
    default_feeds: list[str] = []

    def feed_urls(self) -> list[str]:
        configured = os.getenv(self.env_var, "")
        urls = [url.strip() for url in configured.split(",") if url.strip()]
        return urls or self.default_feeds

    def fetch(self, query: str, limit: int, since_days: int = 7) -> Iterable[RawSourceRecord]:
        since = datetime.combine(date.today() - timedelta(days=since_days), datetime.min.time()).astimezone()
        records: list[RawSourceRecord] = []
        for feed_url in self.feed_urls():
            root = fetch_xml(feed_url)
            for item in root.findall(".//item") + root.findall(".//{http://www.w3.org/2005/Atom}entry"):
                title = clean_html(item.findtext("title") or item.findtext("{http://www.w3.org/2005/Atom}title"))
                description = clean_html(
                    item.findtext("description")
                    or item.findtext("summary")
                    or item.findtext("{http://www.w3.org/2005/Atom}summary")
                    or item.findtext("{http://www.w3.org/2005/Atom}content")
                )
                haystack = f"{title} {description}".lower()
                if query and query.lower() not in haystack:
                    continue
                published = (
                    item.findtext("pubDate")
                    or item.findtext("published")
                    or item.findtext("{http://www.w3.org/2005/Atom}published")
                    or item.findtext("{http://www.w3.org/2005/Atom}updated")
                )
                parsed = parse_datetime(published)
                if parsed and parsed < since:
                    continue
                link = item.findtext("link") or ""
                if not link:
                    atom_link = item.find("{http://www.w3.org/2005/Atom}link")
                    link = atom_link.attrib.get("href", "") if atom_link is not None else ""
                payload = {
                    "title": title,
                    "description": description,
                    "published": published,
                    "link": link,
                    "feed_url": feed_url,
                }
                records.append(
                    RawSourceRecord(
                        source_name=self.source_name,
                        source_type=self.source_type,
                        source_url=link or feed_url,
                        external_id=link or title,
                        payload=payload,
                    )
                )
                if len(records) >= limit:
                    return records
        return records

    def normalize(self, record: RawSourceRecord, channel: str | None = None) -> SourcePacket:
        payload = record.payload
        title = payload.get("title") or record.external_id
        raw_text = payload.get("description") or ""
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
                "feed_url": payload.get("feed_url"),
            },
        )


class BusinessWireConnector(FeedConnector):
    source_id = "business_wire"
    source_name = "Business Wire"
    source_type = "press_release"
    env_var = "AGENTVC_BUSINESS_WIRE_FEEDS"


class SubstackConnector(FeedConnector):
    source_id = "substack"
    source_name = "Substack"
    source_type = "newsletter"
    env_var = "AGENTVC_SUBSTACK_FEEDS"


class VCConfidenceFeedConnector(FeedConnector):
    source_id = "vc_confidence_feed"
    source_name = "VC Confidence Feed"
    source_type = "vc_signal"
    default_channel = "vc_confidence"
    env_var = "AGENTVC_VC_CONFIDENCE_FEEDS"
    default_feeds = [
        "https://news.google.com/rss/search?q=biotech%20venture%20capital%20funding",
        "https://news.google.com/rss/search?q=biopharma%20startup%20series%20A",
    ]


class MarketBackgroundFeedConnector(FeedConnector):
    source_id = "market_background_feed"
    source_name = "Market Background Feed"
    source_type = "market_background"
    default_channel = "market_background"
    env_var = "AGENTVC_MARKET_BACKGROUND_FEEDS"
    default_feeds = [
        "https://news.google.com/rss/search?q=biotech%20market%20FDA",
        "https://news.google.com/rss/search?q=biopharma%20partnership%20licensing",
    ]
