from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from agentvc_generator.models import RawSourceRecord, SourcePacket, utc_now_iso


class GeneratorStore:
    def __init__(self, db_path: str | Path = "data/generator.sqlite"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self.migrate()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "GeneratorStore":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def migrate(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS ingestion_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                connector_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                query TEXT,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                status TEXT NOT NULL,
                error TEXT
            );

            CREATE TABLE IF NOT EXISTS raw_source_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_url TEXT NOT NULL,
                external_id TEXT NOT NULL,
                checksum TEXT NOT NULL UNIQUE,
                fetched_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS source_packets (
                packet_id TEXT PRIMARY KEY,
                channel TEXT NOT NULL,
                source_name TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_url TEXT NOT NULL,
                external_id TEXT NOT NULL,
                title TEXT NOT NULL,
                raw_text TEXT NOT NULL,
                published_at TEXT,
                fetched_at TEXT NOT NULL,
                entities_json TEXT NOT NULL,
                links_json TEXT NOT NULL,
                provenance_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_source_packets_channel ON source_packets(channel);
            CREATE INDEX IF NOT EXISTS idx_source_packets_source ON source_packets(source_name);
            CREATE INDEX IF NOT EXISTS idx_source_packets_external ON source_packets(external_id);
            """
        )
        self.connection.commit()

    def start_run(self, connector_id: str, channel: str, query: str | None) -> int:
        cursor = self.connection.execute(
            """
            INSERT INTO ingestion_runs(connector_id, channel, query, started_at, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (connector_id, channel, query, utc_now_iso(), "running"),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def finish_run(self, run_id: int, status: str, error: str | None = None) -> None:
        self.connection.execute(
            """
            UPDATE ingestion_runs
            SET ended_at = ?, status = ?, error = ?
            WHERE id = ?
            """,
            (utc_now_iso(), status, error, run_id),
        )
        self.connection.commit()

    def save_raw_record(self, record: RawSourceRecord) -> None:
        self.connection.execute(
            """
            INSERT OR IGNORE INTO raw_source_records(
                source_name, source_type, source_url, external_id, checksum, fetched_at, payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.source_name,
                record.source_type,
                record.source_url,
                record.external_id,
                record.checksum,
                record.fetched_at,
                json.dumps(record.payload, sort_keys=True),
            ),
        )
        self.connection.commit()

    def save_packet(self, packet: SourcePacket) -> None:
        self.connection.execute(
            """
            INSERT OR REPLACE INTO source_packets(
                packet_id, channel, source_name, source_type, source_url, external_id, title,
                raw_text, published_at, fetched_at, entities_json, links_json, provenance_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                packet.packet_id,
                packet.channel,
                packet.source_name,
                packet.source_type,
                packet.source_url,
                packet.external_id,
                packet.title,
                packet.raw_text,
                packet.published_at,
                packet.fetched_at,
                json.dumps([entity.to_dict() for entity in packet.entities], sort_keys=True),
                json.dumps([link.to_dict() for link in packet.links], sort_keys=True),
                json.dumps(packet.provenance, sort_keys=True),
            ),
        )
        self.connection.commit()

    def list_packets(self) -> list[sqlite3.Row]:
        cursor = self.connection.execute(
            """
            SELECT *
            FROM source_packets
            ORDER BY fetched_at DESC, title ASC
            """
        )
        return list(cursor.fetchall())

    def list_runs(self, limit: int = 20) -> list[sqlite3.Row]:
        cursor = self.connection.execute(
            """
            SELECT *
            FROM ingestion_runs
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return list(cursor.fetchall())

    def source_counts(self) -> dict[tuple[str, str], int]:
        cursor = self.connection.execute(
            """
            SELECT channel, source_name, COUNT(*) AS count
            FROM source_packets
            GROUP BY channel, source_name
            """
        )
        return {(row["channel"], row["source_name"]): int(row["count"]) for row in cursor.fetchall()}

    def source_run_status(self) -> dict[tuple[str, str], dict]:
        cursor = self.connection.execute(
            """
            SELECT connector_id, channel, started_at, ended_at, status, error, query
            FROM ingestion_runs
            ORDER BY started_at DESC
            """
        )
        statuses: dict[tuple[str, str], dict] = {}
        for row in cursor.fetchall():
            key = (row["channel"], row["connector_id"])
            if key not in statuses:
                statuses[key] = dict(row)
        return statuses

    def knowledge_tree(self, packet_limit: int = 200) -> dict:
        rows = self.connection.execute(
            """
            SELECT *
            FROM source_packets
            ORDER BY channel ASC, source_name ASC, fetched_at DESC
            LIMIT ?
            """,
            (packet_limit,),
        ).fetchall()

        channels: dict[str, dict] = {}
        for row in rows:
            channel = channels.setdefault(
                row["channel"],
                {
                    "id": row["channel"],
                    "name": row["channel"],
                    "packet_count": 0,
                    "sources": {},
                },
            )
            channel["packet_count"] += 1
            source = channel["sources"].setdefault(
                row["source_name"],
                {
                    "name": row["source_name"],
                    "source_type": row["source_type"],
                    "packet_count": 0,
                    "packets": [],
                },
            )
            source["packet_count"] += 1
            source["packets"].append(
                {
                    "packet_id": row["packet_id"],
                    "title": row["title"],
                    "source_type": row["source_type"],
                    "source_url": row["source_url"],
                    "external_id": row["external_id"],
                    "published_at": row["published_at"],
                    "fetched_at": row["fetched_at"],
                    "raw_text": row["raw_text"],
                    "entities": json.loads(row["entities_json"]),
                    "links": json.loads(row["links_json"]),
                    "provenance": json.loads(row["provenance_json"]),
                }
            )

        return {
            "channels": [
                {
                    **channel,
                    "sources": list(channel["sources"].values()),
                }
                for channel in channels.values()
            ]
        }

    def graph(self, packet_limit: int = 120) -> dict[str, list[dict]]:
        packets = self.connection.execute(
            """
            SELECT *
            FROM source_packets
            ORDER BY fetched_at DESC
            LIMIT ?
            """,
            (packet_limit,),
        ).fetchall()

        nodes: dict[str, dict] = {}
        edges: list[dict] = []

        def add_node(node_id: str, label: str, node_type: str, meta: dict | None = None) -> None:
            nodes.setdefault(
                node_id,
                {
                    "id": node_id,
                    "label": label,
                    "type": node_type,
                    "meta": meta or {},
                },
            )

        for packet in packets:
            channel_id = f"channel:{packet['channel']}"
            source_id = f"source:{packet['source_name']}"
            packet_id = f"packet:{packet['packet_id']}"
            add_node(channel_id, packet["channel"], "channel")
            add_node(source_id, packet["source_name"], "source")
            add_node(
                packet_id,
                packet["title"],
                "packet",
                {
                    "source_url": packet["source_url"],
                    "source_type": packet["source_type"],
                    "published_at": packet["published_at"],
                },
            )
            edges.append({"source": channel_id, "target": source_id, "label": "contains"})
            edges.append({"source": source_id, "target": packet_id, "label": "emits"})
            for entity in json.loads(packet["entities_json"]):
                entity_id = f"entity:{entity['entity_type']}:{entity['text']}"
                add_node(entity_id, entity["text"], entity["entity_type"])
                edges.append({"source": packet_id, "target": entity_id, "label": "mentions"})

        unique_edges = {}
        for edge in edges:
            unique_edges[(edge["source"], edge["target"], edge["label"])] = edge
        return {"nodes": list(nodes.values()), "edges": list(unique_edges.values())}
