from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from agentvc_generator.cli import ingest_one
from agentvc_generator.connectors.registry import CONNECTORS
from agentvc_generator.source_catalog import SourceCatalog
from agentvc_generator.storage import GeneratorStore


ADMIN_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AgentVC Generator Admin</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --ink: #1c2430;
      --muted: #667085;
      --line: #d9dee7;
      --blue: #2364aa;
      --green: #287d4f;
      --amber: #a86400;
      --red: #b42318;
      --violet: #6b4bbf;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font: 14px/1.45 system-ui, -apple-system, Segoe UI, sans-serif;
      background: var(--bg);
      color: var(--ink);
    }
    header {
      height: 56px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 20px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }
    h1 { font-size: 17px; margin: 0; }
    main {
      display: grid;
      grid-template-columns: minmax(320px, 430px) 1fr;
      gap: 14px;
      padding: 14px;
      min-height: calc(100vh - 56px);
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      min-width: 0;
    }
    .left {
      display: grid;
      grid-template-rows: auto 1fr;
      gap: 14px;
      min-height: 0;
    }
    .panel-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding: 12px;
      border-bottom: 1px solid var(--line);
    }
    .panel-head h2 { font-size: 14px; margin: 0; }
    .controls {
      display: grid;
      grid-template-columns: 1fr 74px 74px;
      gap: 8px;
      padding: 12px;
      border-bottom: 1px solid var(--line);
    }
    input, select {
      width: 100%;
      height: 34px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0 9px;
      background: #fff;
      color: var(--ink);
    }
    button {
      height: 34px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--ink);
      cursor: pointer;
      white-space: nowrap;
    }
    button.primary {
      border-color: var(--blue);
      background: var(--blue);
      color: #fff;
    }
    button:disabled { opacity: .55; cursor: wait; }
    .channels {
      overflow: auto;
      max-height: calc(100vh - 210px);
      padding: 10px;
    }
    details {
      border: 1px solid var(--line);
      border-radius: 8px;
      margin-bottom: 10px;
      background: #fff;
    }
    summary {
      padding: 10px;
      cursor: pointer;
      font-weight: 650;
    }
    .source {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 8px;
      align-items: center;
      padding: 9px 10px;
      border-top: 1px solid var(--line);
    }
    .source-name { font-weight: 600; }
    .source-meta { color: var(--muted); font-size: 12px; margin-top: 2px; }
    .status {
      display: inline-block;
      padding: 2px 6px;
      border-radius: 999px;
      background: #eef2f7;
      color: #344054;
      font-size: 12px;
    }
    .status.yes { background: #e8f5ee; color: var(--green); }
    .status.no { background: #fff3e2; color: var(--amber); }
    .right {
      display: grid;
      grid-template-rows: minmax(560px, 1fr) 260px;
      gap: 14px;
      min-height: 0;
    }
    #graphWrap { position: relative; min-height: 560px; overflow: hidden; }
    .graph-legend {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-bottom: 1px solid var(--line);
      color: var(--muted);
      font-size: 12px;
    }
    .legend-item { display: inline-flex; align-items: center; gap: 5px; }
    .legend-dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
    .graph-detail {
      min-height: 44px;
      padding: 8px 12px;
      border-top: 1px solid var(--line);
      color: var(--muted);
      font-size: 12px;
      background: #fff;
    }
    svg { width: 100%; height: calc(100% - 130px); min-height: 430px; display: block; background: #fbfcfe; }
    .graph-label { font-size: 11px; fill: #1c2430; pointer-events: none; }
    .column-title { font-size: 12px; fill: #667085; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; }
    .column-bg { fill: #f3f6fa; stroke: #e3e8ef; }
    .edge { fill: none; stroke: #a9b4c2; stroke-width: 1.2; opacity: .58; }
    .edge.strong { stroke: #2364aa; stroke-width: 1.8; opacity: .9; }
    .node-card { stroke: #fff; stroke-width: 1.5; cursor: pointer; filter: drop-shadow(0 1px 2px rgba(16,24,40,.12)); }
    .packet { fill: var(--blue); }
    .sourceNode { fill: var(--green); }
    .channelNode { fill: var(--violet); }
    .entityNode { fill: #cc6b2c; }
    .node-caption { font-size: 10px; fill: #fff; pointer-events: none; font-weight: 650; }
    .node-subcaption { font-size: 9px; fill: rgba(255,255,255,.78); pointer-events: none; }
    .bottom {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
      min-height: 0;
    }
    .list {
      overflow: auto;
      height: 210px;
      padding: 10px 12px;
    }
    .row {
      padding: 8px 0;
      border-bottom: 1px solid var(--line);
    }
    .row-title { font-weight: 600; }
    .row-meta { color: var(--muted); font-size: 12px; margin-top: 2px; }
    #toast {
      color: var(--muted);
      min-width: 280px;
      text-align: right;
    }
    @media (max-width: 900px) {
      main, .right, .bottom { grid-template-columns: 1fr; grid-template-rows: auto; }
      #graphWrap { height: 520px; }
      .channels { max-height: none; }
    }
  </style>
</head>
<body>
<header>
  <h1>AgentVC Generator Admin</h1>
  <div id="toast">Loading...</div>
</header>
<main>
  <div class="left">
    <section>
      <div class="panel-head">
        <h2>Refetch</h2>
        <button class="primary" id="watchlistBtn">Run Watchlist</button>
      </div>
      <div class="controls">
        <input id="query" value="glioblastoma immunotherapy" aria-label="Query">
        <input id="days" type="number" min="1" max="90" value="7" aria-label="Days">
        <input id="limit" type="number" min="1" max="50" value="5" aria-label="Limit">
      </div>
    </section>
    <section>
      <div class="panel-head"><h2>Information Channels</h2><button id="refreshBtn">Refresh</button></div>
      <div class="channels" id="channels"></div>
    </section>
  </div>
  <div class="right">
    <section id="graphWrap">
      <div class="panel-head"><h2>Knowledge Graph</h2><span class="status" id="graphStats"></span></div>
      <div class="graph-legend">
        <span class="legend-item"><span class="legend-dot" style="background:#6b4bbf"></span> Channel</span>
        <span class="legend-item"><span class="legend-dot" style="background:#287d4f"></span> Source</span>
        <span class="legend-item"><span class="legend-dot" style="background:#2364aa"></span> Evidence Packet</span>
        <span class="legend-item"><span class="legend-dot" style="background:#cc6b2c"></span> Concept / Entity</span>
      </div>
      <svg id="graph"></svg>
      <div id="graphDetail" class="graph-detail">Select a node to inspect what it represents in the knowledge base.</div>
    </section>
    <div class="bottom">
      <section>
        <div class="panel-head"><h2>Recent Packets</h2></div>
        <div class="list" id="packets"></div>
      </section>
      <section>
        <div class="panel-head"><h2>Ingestion Runs</h2></div>
        <div class="list" id="runs"></div>
      </section>
    </div>
  </div>
</main>
<script>
const toast = document.getElementById('toast');
const state = { catalog: null, graph: null };

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

function setToast(text) { toast.textContent = text; }

async function loadAll() {
  setToast('Refreshing...');
  const [catalog, packets, runs, graph] = await Promise.all([
    api('/api/catalog'),
    api('/api/packets?limit=30'),
    api('/api/runs?limit=20'),
    api('/api/graph?limit=120')
  ]);
  state.catalog = catalog;
  state.graph = graph;
  renderCatalog(catalog);
  renderPackets(packets.packets);
  renderRuns(runs.runs);
  renderGraph(graph);
  setToast(`Loaded ${packets.packets.length} packets`);
}

function renderCatalog(catalog) {
  const root = document.getElementById('channels');
  root.innerHTML = '';
  for (const channel of catalog.channels) {
    const details = document.createElement('details');
    details.open = true;
    const summary = document.createElement('summary');
    summary.textContent = `${channel.name} (${channel.sources.length})`;
    details.appendChild(summary);
    for (const source of channel.sources) {
      const row = document.createElement('div');
      row.className = 'source';
      const left = document.createElement('div');
      left.innerHTML = `<div class="source-name">${source.name}</div>
        <div class="source-meta">${source.id} | ${source.status} | packets: ${source.count}</div>`;
      const right = document.createElement('div');
      const badge = document.createElement('span');
      badge.className = `status ${source.implemented ? 'yes' : 'no'}`;
      badge.textContent = source.implemented ? 'ready' : 'not ready';
      const btn = document.createElement('button');
      btn.textContent = 'Refetch';
      btn.disabled = !source.implemented;
      btn.onclick = () => refetch(source.id, channel.id);
      right.appendChild(badge);
      right.appendChild(document.createTextNode(' '));
      right.appendChild(btn);
      row.appendChild(left);
      row.appendChild(right);
      details.appendChild(row);
    }
    root.appendChild(details);
  }
}

async function refetch(source, channel) {
  const query = document.getElementById('query').value.trim();
  const limit = Number(document.getElementById('limit').value || 5);
  const days = Number(document.getElementById('days').value || 7);
  setToast(`Fetching ${source}...`);
  await api('/api/refetch', {
    method: 'POST',
    body: JSON.stringify({ source, channel, query, limit, days })
  });
  await loadAll();
}

async function runWatchlist() {
  const btn = document.getElementById('watchlistBtn');
  btn.disabled = true;
  setToast('Running watchlist...');
  try {
    await api('/api/refetch-watchlist', { method: 'POST', body: JSON.stringify({ days: Number(document.getElementById('days').value || 7) }) });
    await loadAll();
  } finally {
    btn.disabled = false;
  }
}

function renderPackets(packets) {
  const root = document.getElementById('packets');
  root.innerHTML = packets.map(packet => `<div class="row">
    <div class="row-title">${packet.title}</div>
    <div class="row-meta">${packet.channel} | ${packet.source_name} | ${packet.source_type}</div>
  </div>`).join('');
}

function renderRuns(runs) {
  const root = document.getElementById('runs');
  root.innerHTML = runs.map(run => `<div class="row">
    <div class="row-title">${run.connector_id} | ${run.status}</div>
    <div class="row-meta">${run.channel} | ${run.query || ''} | ${run.started_at}</div>
  </div>`).join('');
}

function renderGraph(graph) {
  const svg = document.getElementById('graph');
  const wrap = document.getElementById('graphWrap');
  const width = Math.max(860, wrap.clientWidth);
  const height = Math.max(430, wrap.clientHeight - 130);
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.innerHTML = '';
  const degree = new Map();
  for (const edge of graph.edges) {
    degree.set(edge.source, (degree.get(edge.source) || 0) + 1);
    degree.set(edge.target, (degree.get(edge.target) || 0) + 1);
  }

  const layerOf = node => {
    if (node.type === 'channel' || node.type === 'source' || node.type === 'packet') return node.type;
    return 'concept';
  };
  const nodeClass = layer => ({ channel: 'channelNode', source: 'sourceNode', packet: 'packet', concept: 'entityNode' }[layer]);
  const short = (text, max = 30) => text && text.length > max ? `${text.slice(0, max - 1)}...` : (text || '');
  const byIdAll = new Map(graph.nodes.map(node => [node.id, node]));
  const packets = graph.nodes.filter(node => layerOf(node) === 'packet').slice(0, 34);
  const packetIds = new Set(packets.map(node => node.id));
  const concepts = graph.nodes
    .filter(node => layerOf(node) === 'concept')
    .filter(node => graph.edges.some(edge => packetIds.has(edge.source) && edge.target === node.id))
    .sort((a, b) => (degree.get(b.id) || 0) - (degree.get(a.id) || 0))
    .slice(0, 34);
  const sourceIds = new Set(graph.edges.filter(edge => packetIds.has(edge.target)).map(edge => edge.source));
  const channelIds = new Set(graph.edges.filter(edge => sourceIds.has(edge.target)).map(edge => edge.source));
  const selected = graph.nodes.filter(node =>
    packetIds.has(node.id) || sourceIds.has(node.id) || channelIds.has(node.id) || concepts.some(concept => concept.id === node.id)
  );
  const allowed = new Set(selected.map(node => node.id));
  const edges = graph.edges.filter(edge => allowed.has(edge.source) && allowed.has(edge.target));
  document.getElementById('graphStats').textContent = `${selected.length} nodes / ${edges.length} edges`;

  const columns = [
    { key: 'channel', title: 'Information Channels', x: 26, w: 168 },
    { key: 'source', title: 'Sources', x: 225, w: 180 },
    { key: 'packet', title: 'Evidence Packets', x: 438, w: 245 },
    { key: 'concept', title: 'Linked Concepts', x: width - 244, w: 218 }
  ];
  for (const col of columns) {
    const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    bg.setAttribute('class', 'column-bg');
    bg.setAttribute('x', col.x);
    bg.setAttribute('y', 16);
    bg.setAttribute('width', col.w);
    bg.setAttribute('height', height - 28);
    bg.setAttribute('rx', 8);
    svg.appendChild(bg);
    const title = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    title.setAttribute('class', 'column-title');
    title.setAttribute('x', col.x + 12);
    title.setAttribute('y', 38);
    title.textContent = col.title;
    svg.appendChild(title);
  }

  const groups = { channel: [], source: [], packet: [], concept: [] };
  for (const node of selected) groups[layerOf(node)].push(node);
  for (const key of Object.keys(groups)) {
    groups[key].sort((a, b) => {
      if (key === 'concept') return (degree.get(b.id) || 0) - (degree.get(a.id) || 0);
      return a.label.localeCompare(b.label);
    });
  }

  const positioned = new Map();
  for (const col of columns) {
    const items = groups[col.key];
    const gap = Math.max(30, Math.min(58, (height - 82) / Math.max(1, items.length)));
    items.forEach((node, index) => {
      positioned.set(node.id, {
        ...node,
        layer: col.key,
        x: col.x + 12,
        y: 56 + index * gap,
        w: col.w - 24,
        h: col.key === 'packet' ? 36 : 30
      });
    });
  }

  for (const edge of edges) {
    const a = positioned.get(edge.source);
    const b = positioned.get(edge.target);
    if (!a || !b) continue;
    const x1 = a.x + a.w;
    const y1 = a.y + a.h / 2;
    const x2 = b.x;
    const y2 = b.y + b.h / 2;
    const mid = Math.max(20, (x2 - x1) / 2);
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('class', edge.label === 'mentions' ? 'edge strong' : 'edge');
    path.setAttribute('d', `M ${x1} ${y1} C ${x1 + mid} ${y1}, ${x2 - mid} ${y2}, ${x2} ${y2}`);
    svg.appendChild(path);
  }

  for (const node of positioned.values()) {
    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    rect.setAttribute('class', `node-card ${nodeClass(node.layer)}`);
    rect.setAttribute('x', node.x);
    rect.setAttribute('y', node.y);
    rect.setAttribute('width', node.w);
    rect.setAttribute('height', node.h);
    rect.setAttribute('rx', 6);
    rect.onclick = () => {
      const meta = node.meta || {};
      document.getElementById('graphDetail').textContent =
        `${node.layer.toUpperCase()}: ${node.label}` +
        `${meta.source_type ? ` | ${meta.source_type}` : ''}` +
        `${meta.published_at ? ` | published ${meta.published_at}` : ''}` +
        `${meta.source_url ? ` | ${meta.source_url}` : ''}`;
    };
    svg.appendChild(rect);
    const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    label.setAttribute('class', 'node-caption');
    label.setAttribute('x', node.x + 8);
    label.setAttribute('y', node.y + 15);
    label.textContent = short(node.label, node.layer === 'packet' ? 34 : 24);
    svg.appendChild(label);
    const sub = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    sub.setAttribute('class', 'node-subcaption');
    sub.setAttribute('x', node.x + 8);
    sub.setAttribute('y', node.y + (node.layer === 'packet' ? 29 : 25));
    sub.textContent = node.layer === 'concept' ? node.type : `${degree.get(node.id) || 0} links`;
    svg.appendChild(sub);
  }
}

document.getElementById('refreshBtn').onclick = loadAll;
document.getElementById('watchlistBtn').onclick = runWatchlist;
loadAll().catch(error => setToast(error.message));
</script>
</body>
</html>"""


class AdminHandler(BaseHTTPRequestHandler):
    db_path = "data/generator.sqlite"
    watchlist_path = "config/watchlist.json"

    def log_message(self, format: str, *args: object) -> None:
        return

    def send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            body = ADMIN_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        query = parse_qs(parsed.query)
        try:
            if parsed.path == "/api/catalog":
                self.send_json(self.catalog_payload())
            elif parsed.path == "/api/packets":
                limit = int(query.get("limit", ["50"])[0])
                self.send_json(self.packets_payload(limit))
            elif parsed.path == "/api/runs":
                limit = int(query.get("limit", ["20"])[0])
                self.send_json(self.runs_payload(limit))
            elif parsed.path == "/api/graph":
                limit = int(query.get("limit", ["120"])[0])
                with GeneratorStore(self.db_path) as store:
                    self.send_json(store.graph(limit))
            else:
                self.send_json({"error": "not found"}, status=404)
        except Exception as error:
            self.send_json({"error": str(error)}, status=500)

    def do_POST(self) -> None:
        try:
            if self.path == "/api/refetch":
                body = self.read_json()
                count, status = ingest_one(
                    db=self.db_path,
                    source_id=body["source"],
                    channel=body.get("channel"),
                    query=body.get("query", ""),
                    limit=int(body.get("limit", 5)),
                    days=int(body.get("days", 7)),
                )
                self.send_json({"count": count, "status": status})
            elif self.path == "/api/refetch-watchlist":
                body = self.read_json()
                days = int(body.get("days", 7))
                results = []
                watchlist = json.loads(Path(self.watchlist_path).read_text(encoding="utf-8"))
                for item in watchlist.get("queries", []):
                    count, status = ingest_one(
                        db=self.db_path,
                        source_id=item["source"],
                        channel=item.get("channel"),
                        query=item.get("query", ""),
                        limit=int(item.get("limit", 5)),
                        days=int(item.get("days", days)),
                    )
                    results.append({**item, "count": count, "status": status})
                self.send_json({"results": results})
            else:
                self.send_json({"error": "not found"}, status=404)
        except Exception as error:
            self.send_json({"error": str(error)}, status=500)

    def catalog_payload(self) -> dict:
        catalog = SourceCatalog()
        with GeneratorStore(self.db_path) as store:
            counts = store.source_counts()
        channels = []
        for channel in catalog.channels():
            sources = []
            for source in channel.get("sources", []):
                sources.append(
                    {
                        **source,
                        "implemented": source["id"] in CONNECTORS,
                        "count": counts.get((channel["id"], source["name"]), 0),
                    }
                )
            channels.append({"id": channel["id"], "name": channel["name"], "sources": sources})
        return {"channels": channels}

    def packets_payload(self, limit: int) -> dict:
        with GeneratorStore(self.db_path) as store:
            packets = [dict(row) for row in store.list_packets()[:limit]]
        return {"packets": packets}

    def runs_payload(self, limit: int) -> dict:
        with GeneratorStore(self.db_path) as store:
            runs = [dict(row) for row in store.list_runs(limit)]
        return {"runs": runs}


def serve(host: str = "127.0.0.1", port: int = 8000, db_path: str | None = None, watchlist_path: str | None = None) -> ThreadingHTTPServer:
    AdminHandler.db_path = db_path or os.getenv("AGENTVC_DB_PATH", "data/generator.sqlite")
    AdminHandler.watchlist_path = watchlist_path or "config/watchlist.json"
    server = ThreadingHTTPServer((host, port), AdminHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
