from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

from agentvc_generator.connectors.base import SourceConnector
from agentvc_generator.connectors.http import fetch_xml
from agentvc_generator.entities import extract_entity_mentions, mentions_to_links
from agentvc_generator.models import RawSourceRecord, SourcePacket


class PubMedConnector(SourceConnector):
    source_id = "pubmed"
    source_name = "PubMed"
    source_type = "paper"
    default_channel = "bioscience"

    def fetch(self, query: str, limit: int, since_days: int = 7) -> Iterable[RawSourceRecord]:
        since = date.today() - timedelta(days=since_days)
        search_root = fetch_xml(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            {
                "db": "pubmed",
                "term": query,
                "retmode": "xml",
                "retmax": limit,
                "sort": "pub+date",
                "datetype": "pdat",
                "mindate": since.isoformat(),
                "maxdate": date.today().isoformat(),
            },
        )
        ids = [node.text for node in search_root.findall(".//Id") if node.text]
        if not ids:
            return []

        fetch_root = fetch_xml(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
            {
                "db": "pubmed",
                "id": ",".join(ids),
                "retmode": "xml",
            },
        )

        records: list[RawSourceRecord] = []
        for article in fetch_root.findall(".//PubmedArticle"):
            pmid = article.findtext(".//PMID") or ""
            title = "".join(article.findtext(".//ArticleTitle") or "").strip()
            abstract_parts = [
                "".join(node.itertext()).strip()
                for node in article.findall(".//Abstract/AbstractText")
                if "".join(node.itertext()).strip()
            ]
            payload = {
                "pmid": pmid,
                "title": title,
                "abstract": "\n".join(abstract_parts),
                "journal": article.findtext(".//Journal/Title"),
                "publication_year": article.findtext(".//PubDate/Year"),
                "authors": [
                    " ".join(
                        part
                        for part in [
                            author.findtext("ForeName"),
                            author.findtext("LastName"),
                        ]
                        if part
                    )
                    for author in article.findall(".//AuthorList/Author")
                ],
            }
            records.append(
                RawSourceRecord(
                    source_name=self.source_name,
                    source_type=self.source_type,
                    source_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    external_id=pmid,
                    payload=payload,
                )
            )
        return records

    def normalize(self, record: RawSourceRecord, channel: str | None = None) -> SourcePacket:
        payload = record.payload
        title = payload.get("title") or f"PubMed {record.external_id}"
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
            published_at=payload.get("publication_year"),
            fetched_at=record.fetched_at,
            entities=mentions,
            links=mentions_to_links(mentions),
            provenance={
                "raw_checksum": record.checksum,
                "connector": self.source_id,
                "connector_version": "0.1.0",
            },
        )
