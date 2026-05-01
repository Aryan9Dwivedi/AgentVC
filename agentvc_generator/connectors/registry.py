from __future__ import annotations

from agentvc_generator.connectors.arxiv import ArxivConnector
from agentvc_generator.connectors.base import SourceConnector
from agentvc_generator.connectors.biorxiv import BiorxivConnector
from agentvc_generator.connectors.clinical_trials import ClinicalTrialsConnector
from agentvc_generator.connectors.crossref import AACRConnector, AANConnector, ASCOConnector, SSRNConnector
from agentvc_generator.connectors.feeds import BusinessWireConnector, SubstackConnector
from agentvc_generator.connectors.google_patents import GooglePatentsConnector
from agentvc_generator.connectors.ictrp import ICTRPConnector
from agentvc_generator.connectors.pubmed import PubMedConnector
from agentvc_generator.connectors.unpaywall import UnpaywallConnector


CONNECTORS: dict[str, type[SourceConnector]] = {
    PubMedConnector.source_id: PubMedConnector,
    ClinicalTrialsConnector.source_id: ClinicalTrialsConnector,
    ArxivConnector.source_id: ArxivConnector,
    BiorxivConnector.source_id: BiorxivConnector,
    GooglePatentsConnector.source_id: GooglePatentsConnector,
    SSRNConnector.source_id: SSRNConnector,
    ASCOConnector.source_id: ASCOConnector,
    AACRConnector.source_id: AACRConnector,
    AANConnector.source_id: AANConnector,
    BusinessWireConnector.source_id: BusinessWireConnector,
    SubstackConnector.source_id: SubstackConnector,
    ICTRPConnector.source_id: ICTRPConnector,
    UnpaywallConnector.source_id: UnpaywallConnector,
}


def get_connector(source_id: str) -> SourceConnector:
    connector_class = CONNECTORS.get(source_id)
    if connector_class is None:
        available = ", ".join(sorted(CONNECTORS))
        raise KeyError(f"No implemented connector for '{source_id}'. Available: {available}")
    return connector_class()
