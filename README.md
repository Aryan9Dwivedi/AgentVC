# AgentVC Generator

The Generator is the raw supply ingestion point for AgentVC. It collects source material from information channels, preserves provenance, normalizes records into `SourcePacket` objects, and exposes a local admin UI for refetching sources and inspecting the knowledge base.

It does not judge quality, investment value, or scientific validity. Those jobs belong to later Evaluator and Discriminator agents.

## Current Channels

- Bio Medical
- Financial Fiscal
- VC Confidence
- Market and Background
- Scientific Risk
- Patent

Implemented connector paths include:

- PubMed
- ClinicalTrials.gov
- arXiv
- bioRxiv
- Google Patents
- SSRN metadata
- ASCO/AACR/AAN conference archives
- Business Wire feed ingestion
- Substack feed ingestion
- ICTRP
- SEC EDGAR
- Yahoo Finance market quote context
- VC confidence RSS feeds
- Market/background RSS feeds
- Unpaywall DOI helper

## Quick Start

Windows / PowerShell:

```powershell
python -m agentvc_generator list-sources
python -m agentvc_generator run-watchlist --once
python -m agentvc_generator serve --port 8000
python -m agentvc_generator ingest --source pubmed --query "glioblastoma immunotherapy" --limit 5
python -m agentvc_generator ingest --source clinicaltrials --query "glioblastoma" --limit 5
```

macOS / Terminal:

```bash
python3 -m agentvc_generator list-sources
python3 -m agentvc_generator run-watchlist --once
python3 -m agentvc_generator serve --port 8000
python3 -m agentvc_generator ingest --source pubmed --query "glioblastoma immunotherapy" --limit 5
python3 -m agentvc_generator ingest --source clinicaltrials --query "glioblastoma" --limit 5
```

Default storage is local SQLite at `data/generator.sqlite`.

The local admin app runs at `http://127.0.0.1:8000` and provides:

- channel/source inventory
- source-level refetch
- watchlist refetch
- recent packet and ingestion-run views
- detailed knowledge-base tree from channel -> source -> packet -> entities/provenance

For repeated polling:

Windows / PowerShell:

```powershell
python -m agentvc_generator run-watchlist --interval-minutes 60
```

macOS / Terminal:

```bash
python3 -m agentvc_generator run-watchlist --interval-minutes 60
```

Edit `config/watchlist.json` to add source/channel/query combinations.

## Source Access Notes

- Google Patents uses a best-effort public Google Patents metadata endpoint. Production patent coverage should move to a licensed or official patent data provider.
- SSRN and conference sources use Crossref metadata search as a first pass.
- Business Wire requires configured authorized RSS/Atom feeds in `AGENTVC_BUSINESS_WIRE_FEEDS`.
- Substack requires configured public/authorized publication RSS feeds in `AGENTVC_SUBSTACK_FEEDS`.
- VC Confidence and Market Background have default Google News RSS searches and can also read configured RSS/Atom feeds.
- SEC EDGAR works best when queries contain public-company tickers such as `MRNA, VRTX, REGN`.
- Yahoo Finance is best-effort public quote context; use a licensed market data provider for production.
- Unpaywall is a helper for legal open-access discovery by DOI, not a paywall bypass.
- ICTRP uses public search portal parsing; the official XML web service may require a WHO access arrangement.
