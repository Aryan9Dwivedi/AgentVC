from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from agentvc_generator.connectors.registry import CONNECTORS, get_connector
from agentvc_generator.source_catalog import SourceCatalog
from agentvc_generator.storage import GeneratorStore


def list_sources() -> int:
    catalog = SourceCatalog()
    for source in catalog.sources():
        implemented = "yes" if source["id"] in CONNECTORS else "no"
        print(
            f"{source['channel']:<18} {source['id']:<24} "
            f"status={source['status']:<24} implemented={implemented}"
        )
    return 0


def ingest(args: argparse.Namespace) -> int:
    catalog = SourceCatalog()
    source = catalog.find_source(args.source, args.channel)
    if source is None:
        print(f"Unknown source '{args.source}'. Run list-sources to inspect the catalog.", file=sys.stderr)
        return 2
    if args.source not in CONNECTORS:
        print(
            f"Source '{args.source}' is cataloged but not implemented yet. "
            f"Status: {source.get('status')}. Notes: {source.get('notes', '')}",
            file=sys.stderr,
        )
        return 2

    connector = get_connector(args.source)
    channel = args.channel or source["channel"] or connector.default_channel
    store = GeneratorStore(args.db)
    run_id = store.start_run(connector.source_id, channel, args.query)
    try:
        count = 0
        for raw_record in connector.fetch(args.query, args.limit, since_days=args.days):
            packet = connector.normalize(raw_record, channel=channel)
            store.save_raw_record(raw_record)
            store.save_packet(packet)
            count += 1
        store.finish_run(run_id, "success")
        print(f"Ingested {count} packet(s) from {connector.source_name} into {args.db}")
        return 0
    except Exception as error:
        store.finish_run(run_id, "failed", str(error))
        print(f"Ingestion failed: {error}", file=sys.stderr)
        return 1
    finally:
        store.close()


def ingest_one(
    db: str,
    source_id: str,
    query: str,
    limit: int,
    channel: str | None = None,
    days: int = 7,
) -> tuple[int, str]:
    catalog = SourceCatalog()
    source = catalog.find_source(source_id, channel)
    if source is None:
        return 0, f"unknown source {source_id}"
    if source_id not in CONNECTORS:
        return 0, f"source {source_id} not implemented"

    connector = get_connector(source_id)
    resolved_channel = channel or source["channel"] or connector.default_channel
    with GeneratorStore(db) as store:
        run_id = store.start_run(connector.source_id, resolved_channel, query)
        try:
            count = 0
            for raw_record in connector.fetch(query, limit, since_days=days):
                store.save_raw_record(raw_record)
                store.save_packet(connector.normalize(raw_record, channel=resolved_channel))
                count += 1
            store.finish_run(run_id, "success")
            return count, "success"
        except Exception as error:
            store.finish_run(run_id, "failed", str(error))
            return 0, str(error)


def run_watchlist(args: argparse.Namespace) -> int:
    watchlist = json.loads(Path(args.watchlist).read_text(encoding="utf-8"))
    while True:
        total = 0
        for item in watchlist.get("queries", []):
            count, status = ingest_one(
                db=args.db,
                source_id=item["source"],
                channel=item.get("channel"),
                query=item["query"],
                limit=int(item.get("limit", args.limit)),
                days=int(item.get("days", args.days)),
            )
            total += count
            print(
                f"{item.get('channel', ''):<18} {item['source']:<16} "
                f"query={item['query']!r} count={count} status={status}"
            )
        print(f"Watchlist cycle complete. Ingested {total} packet(s).")
        if args.once:
            return 0
        time.sleep(args.interval_minutes * 60)


def serve_admin(args: argparse.Namespace) -> int:
    from agentvc_generator.web import serve

    server = serve(host=args.host, port=args.port, db_path=args.db, watchlist_path=args.watchlist)
    print(f"AgentVC Generator Admin running at http://{args.host}:{args.port}")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        server.shutdown()
        print("Server stopped.")
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentvc-generator")
    parser.set_defaults(func=lambda _args: parser.print_help() or 0)
    parser.add_argument(
        "--db",
        default=os.getenv("AGENTVC_DB_PATH", "data/generator.sqlite"),
        help="Path to local SQLite generator database.",
    )

    subparsers = parser.add_subparsers(dest="command")

    list_parser = subparsers.add_parser("list-sources")
    list_parser.set_defaults(func=lambda args: list_sources())

    ingest_parser = subparsers.add_parser("ingest")
    ingest_parser.add_argument(
        "--db",
        default=os.getenv("AGENTVC_DB_PATH", "data/generator.sqlite"),
        help="Path to local SQLite generator database.",
    )
    ingest_parser.add_argument("--source", required=True, help="Source id, e.g. pubmed or clinicaltrials.")
    ingest_parser.add_argument("--channel", help="Optional channel override.")
    ingest_parser.add_argument("--query", required=True, help="Search query.")
    ingest_parser.add_argument("--limit", type=int, default=10, help="Maximum records to fetch.")
    ingest_parser.add_argument("--days", type=int, default=7, help="Fetch/update window in days.")
    ingest_parser.set_defaults(func=ingest)

    watchlist_parser = subparsers.add_parser("run-watchlist")
    watchlist_parser.add_argument(
        "--db",
        default=os.getenv("AGENTVC_DB_PATH", "data/generator.sqlite"),
        help="Path to local SQLite generator database.",
    )
    watchlist_parser.add_argument(
        "--watchlist",
        default="config/watchlist.json",
        help="JSON watchlist of source/channel/query items.",
    )
    watchlist_parser.add_argument("--limit", type=int, default=5, help="Default limit per query.")
    watchlist_parser.add_argument("--days", type=int, default=7, help="Default fetch/update window in days.")
    watchlist_parser.add_argument(
        "--interval-minutes",
        type=int,
        default=60,
        help="Polling interval for repeated runs.",
    )
    watchlist_parser.add_argument("--once", action="store_true", help="Run one cycle and exit.")
    watchlist_parser.set_defaults(func=run_watchlist)

    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument(
        "--db",
        default=os.getenv("AGENTVC_DB_PATH", "data/generator.sqlite"),
        help="Path to local SQLite generator database.",
    )
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host interface.")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port for the admin UI.")
    serve_parser.add_argument(
        "--watchlist",
        default="config/watchlist.json",
        help="JSON watchlist of source/channel/query items.",
    )
    serve_parser.set_defaults(func=serve_admin)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
