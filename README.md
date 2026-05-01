# AgentVC Generator

The Generator is the raw supply ingestion point for AgentVC. It collects source material from information channels, preserves provenance, normalizes records into `SourcePacket` objects, and exposes a local admin UI for refetching sources and inspecting the knowledge base.

It does not judge quality, investment value, or scientific validity. Those jobs belong to later Evaluator and Discriminator agents.

## Current Channels

- Bioscience
- Scientific Risk
- Financial & Fiscal
- VC Confidence
- Market & Background
- Execution & Team

The first implemented connectors focus on clean public APIs:

- PubMed
- ClinicalTrials.gov
- arXiv
- bioRxiv

Several requested sources are in the catalog but intentionally marked as future/provider-backed because they need paywall, scraping, archive, or licensing decisions:

- Google Patents
- SSRN
- ASCO/AACR/AAN conference archives
- Business Wire
- Substack
- ICTRP

## Quick Start

```powershell
python -m agentvc_generator list-sources
python -m agentvc_generator run-watchlist --once
python -m agentvc_generator serve --port 8000
python -m agentvc_generator ingest --source pubmed --query "glioblastoma immunotherapy" --limit 5
python -m agentvc_generator ingest --source clinicaltrials --query "glioblastoma" --limit 5
```

Default storage is local SQLite at `data/generator.sqlite`.

The local admin app runs at `http://127.0.0.1:8000` and provides:

- channel/source inventory
- source-level refetch
- watchlist refetch
- recent packet and ingestion-run views
- browser-rendered knowledge map from packets, channels, sources, and entity mentions

For repeated polling:

```powershell
python -m agentvc_generator run-watchlist --interval-minutes 60
```

Edit `config/watchlist.json` to add source/channel/query combinations.

## Source Access Notes

- Google Patents uses a best-effort public Google Patents metadata endpoint. Production patent coverage should move to a licensed or official patent data provider.
- SSRN and conference sources use Crossref metadata search as a first pass.
- Business Wire requires configured authorized RSS/Atom feeds in `AGENTVC_BUSINESS_WIRE_FEEDS`.
- Substack requires configured public/authorized publication RSS feeds in `AGENTVC_SUBSTACK_FEEDS`.
- Unpaywall is a helper for legal open-access discovery by DOI, not a paywall bypass.
- ICTRP uses public search portal parsing; the official XML web service may require a WHO access arrangement.
