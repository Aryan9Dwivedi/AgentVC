from __future__ import annotations

import re

from agentvc_generator.models import EntityMention, GraphLink


DISEASE_TERMS = {
    "glioblastoma",
    "cancer",
    "melanoma",
    "lymphoma",
    "leukemia",
    "alzheimer",
    "parkinson",
    "diabetes",
    "fibrosis",
}

STOP_SYMBOLS = {
    "AND",
    "ARE",
    "ARM",
    "BMI",
    "CT",
    "DNA",
    "FDA",
    "FOR",
    "HIV",
    "ICF",
    "IRB",
    "MRI",
    "NCI",
    "NIH",
    "NOT",
    "PET",
    "RNA",
    "THE",
    "WHO",
}


def extract_entity_mentions(text: str) -> list[EntityMention]:
    mentions: dict[tuple[str, str], EntityMention] = {}
    lowered = text.lower()

    for disease in DISEASE_TERMS:
        if disease in lowered:
            mentions[(disease, "disease")] = EntityMention(
                text=disease,
                entity_type="disease",
                confidence=0.6,
            )

    for nct_id in re.findall(r"\bNCT\d{8}\b", text):
        mentions[(nct_id, "trial")] = EntityMention(
            text=nct_id,
            entity_type="trial",
            confidence=1.0,
        )

    for company in re.findall(
        r"\b[A-Z][A-Za-z0-9&.-]+(?:\s+[A-Z][A-Za-z0-9&.-]+){0,4}\s+"
        r"(?:Therapeutics|Biotech|BioPharma|Pharmaceuticals|Pharma|Inc|Corp|Ltd)\b",
        text,
    ):
        mentions[(company, "company")] = EntityMention(
            text=company,
            entity_type="company",
            confidence=0.7,
        )

    for gene in re.findall(r"\b[A-Z][A-Z0-9-]{2,9}\b", text):
        normalized = gene.strip("-")
        if (
            any(char.isalpha() for char in normalized)
            and not normalized.isdigit()
            and normalized not in STOP_SYMBOLS
            and not re.fullmatch(r"[IVX]+", normalized)
        ):
            mentions.setdefault(
                (normalized, "symbol"),
                EntityMention(text=normalized, entity_type="symbol", confidence=0.4),
            )

    return sorted(mentions.values(), key=lambda item: (item.entity_type, item.text.lower()))


def mentions_to_links(mentions: list[EntityMention]) -> list[GraphLink]:
    return [
        GraphLink(
            target=mention.text,
            relationship="mentions",
            target_type=mention.entity_type,
        )
        for mention in mentions
    ]
