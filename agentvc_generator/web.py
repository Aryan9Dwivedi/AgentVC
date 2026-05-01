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
      --bg: #f5f7fa;
      --panel: #ffffff;
      --ink: #172033;
      --muted: #667085;
      --line: #d9e0ea;
      --blue: #1f5f99;
      --green: #21764b;
      --amber: #9b5b00;
      --red: #b42318;
      --purple: #6545ad;
      --soft-blue: #e9f2fb;
      --soft-green: #eaf6ef;
      --soft-amber: #fff4df;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.45 system-ui, -apple-system, Segoe UI, sans-serif;
    }
    header {
      height: 58px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 18px;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
    }
    h1 { font-size: 17px; margin: 0; }
    main {
      display: grid;
      grid-template-columns: 390px 1fr;
      gap: 12px;
      padding: 12px;
      min-height: calc(100vh - 58px);
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      min-width: 0;
    }
    .left, .right { display: grid; gap: 12px; align-content: start; }
    .right { grid-template-rows: minmax(520px, 1fr) 260px; }
    .panel-head {
      min-height: 46px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
    }
    .panel-head h2 { font-size: 14px; margin: 0; }
    .toolbar {
      display: grid;
      grid-template-columns: 1fr 70px 70px;
      gap: 8px;
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
    }
    input {
      width: 100%;
      height: 34px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0 9px;
      background: #fff;
      color: var(--ink);
    }
    button {
      height: 32px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--ink);
      cursor: pointer;
      white-space: nowrap;
    }
    button.primary { background: var(--blue); border-color: var(--blue); color: #fff; }
    button:disabled { opacity: .55; cursor: wait; }
    .scroll { overflow: auto; padding: 10px; }
    .source-list { max-height: calc(100vh - 220px); }
    details {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      margin-bottom: 8px;
    }
    summary {
      cursor: pointer;
      padding: 9px 10px;
      font-weight: 700;
    }
    .source-row {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 8px;
      align-items: start;
      padding: 9px 10px;
      border-top: 1px solid var(--line);
    }
    .title { font-weight: 650; }
    .meta, .small { color: var(--muted); font-size: 12px; }
    .badge {
      display: inline-block;
      padding: 2px 7px;
      border-radius: 999px;
      background: #eef2f7;
      color: #344054;
      font-size: 12px;
      margin-right: 4px;
    }
    .badge.ready { background: var(--soft-green); color: var(--green); }
    .badge.warn { background: var(--soft-amber); color: var(--amber); }
    .badge.fail { background: #fdecec; color: var(--red); }
    .kb-tree { height: 100%; min-height: 520px; overflow: auto; padding: 10px; }
    .tree-channel { border-left: 5px solid var(--purple); }
    .tree-source { margin-left: 18px; border-left: 5px solid var(--green); }
    .tree-packet { margin-left: 36px; border-left: 5px solid var(--blue); }
    .packet-body {
      padding: 0 10px 10px 10px;
      border-top: 1px solid var(--line);
    }
    .entity-list {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin: 8px 0;
    }
    .entity {
      padding: 3px 7px;
      border-radius: 999px;
      background: var(--soft-blue);
      color: var(--blue);
      font-size: 12px;
    }
    .raw-text {
      max-height: 110px;
      overflow: auto;
      padding: 8px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fbfcfe;
      white-space: pre-wrap;
      font-size: 12px;
    }
    .bottom {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      min-height: 0;
    }
    .list { height: 210px; overflow: auto; padding: 10px 12px; }
    .row { padding: 8px 0; border-bottom: 1px solid var(--line); }
    #toast { color: var(--muted); min-width: 280px; text-align: right; }
    a { color: var(--blue); text-decoration: none; }
    @media (max-width: 980px) {
      main, .bottom { grid-template-columns: 1fr; }
      .right { grid-template-rows: auto auto; }
      .kb-tree { min-height: 520px; }
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
        <h2>Refetch Controls</h2>
        <button class="primary" id="watchlistBtn">Run Watchlist</button>
      </div>
      <div class="toolbar">
        <input id="query" value="oncology immunotherapy" aria-label="Query">
        <input id="days" type="number" min="1" max="90" value="7" aria-label="Days">
        <input id="limit" type="number" min="1" max="50" value="5" aria-label="Limit">
      </div>
    </section>
    <section>
      <div class="panel-head">
        <h2>Source Channels</h2>
        <button id="refreshBtn">Refresh</button>
      </div>
      <div class="scroll source-list" id="channels"></div>
    </section>
  </div>
  <div class="right">
    <section>
      <div class="panel-head">
        <h2>Knowledge Base Tree</h2>
        <span class="badge" id="treeStats">0 packets</span>
      </div>
      <div class="kb-tree" id="tree"></div>
    </section>
    <div class="bottom">
      <section>
        <div class="panel-head"><h2>Recent Packets</h2></div>
        <div class="list" id="packets"></div>
      </section>
      <section>
        <div class="panel-head"><h2>Ingestion Runs and Issues</h2></div>
        <div class="list" id="runs"></div>
      </section>
    </div>
  </div>
</main>
<script>
const toast = document.getElementById('toast');
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...options });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

function setToast(text) { toast.textContent = text; }

async function loadAll() {
  setToast('Refreshing...');
  const [catalog, packets, runs, tree] = await Promise.all([
    api('/api/catalog'),
    api('/api/packets?limit=40'),
    api('/api/runs?limit=40'),
    api('/api/tree?limit=250')
  ]);
  renderCatalog(catalog.channels);
  renderPackets(packets.packets);
  renderRuns(runs.runs);
  renderTree(tree.channels);
  setToast('Ready');
}

function statusBadge(source) {
  const run = source.last_run;
  if (!source.implemented) return '<span class="badge warn">not implemented</span>';
  if (!run) return '<span class="badge warn">not fetched</span>';
  if (run.status !== 'success') return '<span class="badge fail">issue</span>';
  return '<span class="badge ready">healthy</span>';
}

function renderCatalog(channels) {
  const root = document.getElementById('channels');
  root.innerHTML = '';
  for (const channel of channels) {
    const details = document.createElement('details');
    details.open = true;
    details.innerHTML = `<summary>${escapeHtml(channel.name)} <span class="badge">${channel.sources.length} sources</span></summary>`;
    for (const source of channel.sources) {
      const row = document.createElement('div');
      row.className = 'source-row';
      const issue = source.last_run && source.last_run.error ? `<div class="small">Issue: ${escapeHtml(source.last_run.error)}</div>` : '';
      row.innerHTML = `
        <div>
          <div class="title">${escapeHtml(source.name)}</div>
          <div class="meta">${escapeHtml(source.id)} | ${escapeHtml(source.status)} | packets: ${source.count}</div>
          <div>${statusBadge(source)}${source.last_run ? `<span class="badge">${escapeHtml(source.last_run.started_at)}</span>` : ''}</div>
          ${issue}
        </div>
        <button ${source.implemented ? '' : 'disabled'} data-source="${escapeHtml(source.id)}" data-channel="${escapeHtml(channel.id)}">Refetch</button>
      `;
      row.querySelector('button').onclick = () => refetch(source.id, channel.id);
      details.appendChild(row);
    }
    root.appendChild(details);
  }
}

async function refetch(source, channel) {
  setToast(`Fetching ${source}...`);
  await api('/api/refetch', {
    method: 'POST',
    body: JSON.stringify({
      source,
      channel,
      query: document.getElementById('query').value.trim(),
      limit: Number(document.getElementById('limit').value || 5),
      days: Number(document.getElementById('days').value || 7)
    })
  });
  await loadAll();
}

async function runWatchlist() {
  const btn = document.getElementById('watchlistBtn');
  btn.disabled = true;
  setToast('Running watchlist...');
  try {
    await api('/api/refetch-watchlist', {
      method: 'POST',
      body: JSON.stringify({ days: Number(document.getElementById('days').value || 7) })
    });
    await loadAll();
  } finally {
    btn.disabled = false;
  }
}

function renderTree(channels) {
  const root = document.getElementById('tree');
  let packetCount = 0;
  root.innerHTML = '';
  if (!channels.length) {
    root.innerHTML = '<div class="meta">No packets yet. Run the watchlist or refetch a source.</div>';
    document.getElementById('treeStats').textContent = '0 packets';
    return;
  }
  for (const channel of channels) {
    packetCount += channel.packet_count;
    const channelEl = document.createElement('details');
    channelEl.className = 'tree-channel';
    channelEl.open = true;
    channelEl.innerHTML = `<summary>${escapeHtml(channel.name)} <span class="badge">${channel.packet_count} packets</span></summary>`;
    for (const source of channel.sources) {
      const sourceEl = document.createElement('details');
      sourceEl.className = 'tree-source';
      sourceEl.open = true;
      sourceEl.innerHTML = `<summary>${escapeHtml(source.name)} <span class="badge">${source.source_type}</span> <span class="badge">${source.packet_count} packets</span></summary>`;
      for (const packet of source.packets) {
        const entities = packet.entities.map(entity => `<span class="entity">${escapeHtml(entity.text)} · ${escapeHtml(entity.entity_type)}</span>`).join('');
        const packetEl = document.createElement('details');
        packetEl.className = 'tree-packet';
        packetEl.innerHTML = `
          <summary>${escapeHtml(packet.title)} <span class="badge">${escapeHtml(packet.source_type)}</span></summary>
          <div class="packet-body">
            <div class="meta">External ID: ${escapeHtml(packet.external_id)} | Published: ${escapeHtml(packet.published_at || 'unknown')} | Fetched: ${escapeHtml(packet.fetched_at)}</div>
            <div class="meta">Source: <a href="${escapeHtml(packet.source_url)}" target="_blank">${escapeHtml(packet.source_url)}</a></div>
            <div class="entity-list">${entities || '<span class="meta">No entities extracted</span>'}</div>
            <div class="raw-text">${escapeHtml(packet.raw_text || 'No raw text extracted.')}</div>
            <div class="meta">Provenance: ${escapeHtml(JSON.stringify(packet.provenance))}</div>
          </div>
        `;
        sourceEl.appendChild(packetEl);
      }
      channelEl.appendChild(sourceEl);
    }
    root.appendChild(channelEl);
  }
  document.getElementById('treeStats').textContent = `${packetCount} packets`;
}

function renderPackets(packets) {
  const root = document.getElementById('packets');
  root.innerHTML = packets.map(packet => `<div class="row">
    <div class="title">${escapeHtml(packet.title)}</div>
    <div class="meta">${escapeHtml(packet.channel)} | ${escapeHtml(packet.source_name)} | ${escapeHtml(packet.source_type)}</div>
  </div>`).join('');
}

function renderRuns(runs) {
  const root = document.getElementById('runs');
  root.innerHTML = runs.map(run => {
    const cls = run.status === 'success' ? 'ready' : 'fail';
    return `<div class="row">
      <div class="title">${escapeHtml(run.connector_id)} <span class="badge ${cls}">${escapeHtml(run.status)}</span></div>
      <div class="meta">${escapeHtml(run.channel)} | ${escapeHtml(run.query || '')} | ${escapeHtml(run.started_at)}</div>
      ${run.error ? `<div class="small">Issue: ${escapeHtml(run.error)}</div>` : ''}
    </div>`;
  }).join('');
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
                limit = int(query.get("limit", ["40"])[0])
                self.send_json(self.runs_payload(limit))
            elif parsed.path == "/api/graph":
                limit = int(query.get("limit", ["120"])[0])
                with GeneratorStore(self.db_path) as store:
                    self.send_json(store.graph(limit))
            elif parsed.path == "/api/tree":
                limit = int(query.get("limit", ["250"])[0])
                with GeneratorStore(self.db_path) as store:
                    self.send_json(store.knowledge_tree(limit))
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
            run_status = store.source_run_status()
        channels = []
        for channel in catalog.channels():
            sources = []
            for source in channel.get("sources", []):
                sources.append(
                    {
                        **source,
                        "implemented": source["id"] in CONNECTORS,
                        "count": counts.get((channel["id"], source["name"]), 0),
                        "last_run": run_status.get((channel["id"], source["id"])),
                    }
                )
            channels.append(
                {
                    "id": channel["id"],
                    "name": channel["name"],
                    "description": channel.get("description", ""),
                    "sources": sources,
                }
            )
        return {"channels": channels}

    def packets_payload(self, limit: int) -> dict:
        with GeneratorStore(self.db_path) as store:
            packets = [dict(row) for row in store.list_packets()[:limit]]
        return {"packets": packets}

    def runs_payload(self, limit: int) -> dict:
        with GeneratorStore(self.db_path) as store:
            runs = [dict(row) for row in store.list_runs(limit)]
        return {"runs": runs}


def serve(
    host: str = "127.0.0.1",
    port: int = 8000,
    db_path: str | None = None,
    watchlist_path: str | None = None,
) -> ThreadingHTTPServer:
    AdminHandler.db_path = db_path or os.getenv("AGENTVC_DB_PATH", "data/generator.sqlite")
    AdminHandler.watchlist_path = watchlist_path or "config/watchlist.json"
    server = ThreadingHTTPServer((host, port), AdminHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
