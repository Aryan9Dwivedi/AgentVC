from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

from agentvc_generator.connectors.base import SourceConnector
from agentvc_generator.connectors.http import fetch_json
from agentvc_generator.entities import extract_entity_mentions, mentions_to_links
from agentvc_generator.models import RawSourceRecord, SourcePacket


class ClinicalTrialsConnector(SourceConnector):
    source_id = "clinicaltrials"
    source_name = "ClinicalTrials.gov"
    source_type = "trial"
    default_channel = "scientific_risk"

    def fetch(self, query: str, limit: int, since_days: int = 7) -> Iterable[RawSourceRecord]:
        since = date.today() - timedelta(days=since_days)
        data = fetch_json(
            "https://clinicaltrials.gov/api/v2/studies",
            {
                "query.term": query,
                "pageSize": limit,
                "format": "json",
                "filter.advanced": f"AREA[LastUpdatePostDate]RANGE[{since.isoformat()},MAX]",
            },
        )
        records: list[RawSourceRecord] = []
        for study in data.get("studies", []):
            protocol = study.get("protocolSection", {})
            identification = protocol.get("identificationModule", {})
            nct_id = identification.get("nctId", "")
            records.append(
                RawSourceRecord(
                    source_name=self.source_name,
                    source_type=self.source_type,
                    source_url=f"https://clinicaltrials.gov/study/{nct_id}",
                    external_id=nct_id,
                    payload=study,
                )
            )
        return records

    def normalize(self, record: RawSourceRecord, channel: str | None = None) -> SourcePacket:
        protocol = record.payload.get("protocolSection", {})
        identification = protocol.get("identificationModule", {})
        status = protocol.get("statusModule", {})
        sponsor = protocol.get("sponsorCollaboratorsModule", {})
        description = protocol.get("descriptionModule", {})
        conditions = protocol.get("conditionsModule", {})
        arms = protocol.get("armsInterventionsModule", {})
        eligibility = protocol.get("eligibilityModule", {})
        references = protocol.get("referencesModule", {})

        title = identification.get("briefTitle") or identification.get("officialTitle") or record.external_id
        text_parts = [
            description.get("briefSummary", ""),
            "Conditions: " + ", ".join(conditions.get("conditions", [])),
            "Interventions: "
            + ", ".join(
                item.get("name", "")
                for item in arms.get("interventions", [])
                if item.get("name")
            ),
            "Eligibility: " + eligibility.get("eligibilityCriteria", ""),
        ]
        raw_text = "\n\n".join(part for part in text_parts if part.strip())
        publications = references.get("references", [])
        mentions = extract_entity_mentions(f"{record.external_id}\n{title}\n{raw_text}")

        return SourcePacket(
            channel=channel or self.default_channel,
            source_name=record.source_name,
            source_type=record.source_type,
            source_url=record.source_url,
            external_id=record.external_id,
            title=title,
            raw_text=raw_text,
            published_at=status.get("studyFirstSubmitDate") or status.get("lastUpdateSubmitDate"),
            fetched_at=record.fetched_at,
            entities=mentions,
            links=mentions_to_links(mentions),
            provenance={
                "raw_checksum": record.checksum,
                "connector": self.source_id,
                "connector_version": "0.1.0",
                "sponsor": sponsor.get("leadSponsor", {}).get("name"),
                "publications": publications,
            },
        )
