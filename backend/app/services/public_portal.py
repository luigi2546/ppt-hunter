import json
from collections import defaultdict
from datetime import datetime
from html import escape
from typing import Callable

from app.core.config import settings
from app.models.document import Document
from app.services.storage import is_remote_storage_enabled, upload_file


PORTAL_INDEX_KEY = "index.html"
PORTAL_MANIFEST_KEY = "portal_manifest.json"


def export_public_portal(documents: list[Document], csv_key: str, json_key: str) -> tuple[str, str]:
    portal_dir = settings.storage_dir / "portal"
    portal_dir.mkdir(parents=True, exist_ok=True)

    manifest = build_manifest(documents, csv_key, json_key)
    manifest_path = portal_dir / PORTAL_MANIFEST_KEY
    index_path = portal_dir / PORTAL_INDEX_KEY

    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    index_path.write_text(build_index_html(settings.public_archive_title), encoding="utf-8")

    if is_remote_storage_enabled():
        upload_file(manifest_path, PORTAL_MANIFEST_KEY, "application/json")
        upload_file(index_path, PORTAL_INDEX_KEY, "text/html")

    return PORTAL_INDEX_KEY, PORTAL_MANIFEST_KEY


def build_manifest(
    documents: list[Document],
    csv_key: str,
    json_key: str,
    download_url_for: Callable[[Document], str] | None = None,
) -> dict[str, object]:
    files_by_day: dict[str, list[dict[str, object]]] = defaultdict(list)
    total_size = 0

    for document in documents:
        if not document.storage_key and (download_url_for is None or not document.file_path):
            continue
        if document.status not in {"downloaded", "ready"} and document.size_bytes is None:
            continue

        day = (document.updated_at or document.created_at or datetime.utcnow()).strftime("%Y-%m-%d")
        size_bytes = document.size_bytes or 0
        storage_key = document.storage_key or f"documents/{document.id}.{document.file_type}"
        total_size += size_bytes
        files_by_day[day].append(
            {
                "id": document.id,
                "title": document.title,
                "key": storage_key,
                "download_url": download_url_for(document) if download_url_for else object_url(storage_key),
                "source_url": document.source_url,
                "file_type": document.file_type,
                "size": size_bytes,
                "slides": document.slide_count,
                "category": document.category,
                "summary": document.summary,
                "sha256": document.sha256,
                "updated_at": document.updated_at.isoformat() if document.updated_at else None,
            }
        )

    days = []
    for day, files in sorted(files_by_day.items(), reverse=True):
        files.sort(key=lambda item: str(item.get("title", "")).lower())
        days.append(
            {
                "day": day,
                "file_count": len(files),
                "size": sum(int(file.get("size") or 0) for file in files),
                "ppt_count": sum(1 for file in files if file.get("file_type") == "ppt"),
                "pptx_count": sum(1 for file in files if file.get("file_type") == "pptx"),
                "files": files,
            }
        )

    return {
        "title": settings.public_archive_title,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "target_files": settings.public_archive_target_files,
        "total_files": sum(int(day["file_count"]) for day in days),
        "total_size": total_size,
        "base_url": settings.public_archive_base_url.rstrip("/") if settings.public_archive_base_url else "",
        "metadata": {
            "csv_key": csv_key,
            "json_key": json_key,
            "csv_url": object_url(csv_key),
            "json_url": object_url(json_key),
        },
        "days": days,
    }


def object_url(key: str) -> str:
    if key.startswith("/"):
        return key
    clean_key = key.lstrip("/")
    if settings.public_archive_base_url:
        return f"{settings.public_archive_base_url.rstrip('/')}/{clean_key}"
    return clean_key


def build_index_html(title: str) -> str:
    safe_title = escape(title)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{safe_title}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      min-height: 100vh;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      background: #f4f6f8;
      color: #172033;
    }}
    header {{
      background: linear-gradient(135deg, #0f5132, #1f7a5a 55%, #234c75);
      color: white;
      padding: 28px 20px;
    }}
    .wrap {{ max-width: 1180px; margin: 0 auto; }}
    .topline {{ display: flex; justify-content: space-between; gap: 16px; align-items: center; flex-wrap: wrap; }}
    h1 {{ font-size: clamp(28px, 4vw, 46px); font-weight: 750; letter-spacing: 0; }}
    .subtitle {{ margin-top: 8px; color: rgba(255,255,255,.82); font-size: 15px; }}
    .actions {{ display: flex; gap: 10px; flex-wrap: wrap; }}
    .button {{
      display: inline-flex;
      align-items: center;
      min-height: 38px;
      border-radius: 6px;
      padding: 8px 12px;
      background: rgba(255,255,255,.14);
      color: white;
      border: 1px solid rgba(255,255,255,.22);
      text-decoration: none;
      font-size: 14px;
      font-weight: 650;
    }}
    .stats {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-top: 24px; }}
    .stat {{ background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.18); border-radius: 8px; padding: 16px; }}
    .number {{ font-size: 30px; font-weight: 760; }}
    .label {{ margin-top: 3px; color: rgba(255,255,255,.78); font-size: 13px; }}
    main {{ padding: 24px 20px 50px; }}
    .toolbar {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      align-items: center;
      margin-bottom: 18px;
    }}
    input {{
      width: 100%;
      min-height: 42px;
      border: 1px solid #d8dee8;
      border-radius: 6px;
      background: white;
      padding: 0 12px;
      font-size: 14px;
      outline: none;
    }}
    input:focus {{ border-color: #1f7a5a; box-shadow: 0 0 0 3px rgba(31,122,90,.14); }}
    .muted {{ color: #667085; font-size: 14px; }}
    .day {{
      background: white;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      margin-bottom: 16px;
      overflow: hidden;
      box-shadow: 0 1px 2px rgba(16, 24, 40, .04);
    }}
    .day-head {{
      display: flex;
      justify-content: space-between;
      gap: 14px;
      align-items: center;
      padding: 18px 20px;
      border-bottom: 1px solid #edf1f5;
      cursor: pointer;
    }}
    .day-title {{ font-size: 18px; font-weight: 720; }}
    .day-meta {{ margin-top: 4px; color: #667085; font-size: 13px; }}
    .pill {{ border-radius: 999px; background: #e7f4ef; color: #0f5132; padding: 6px 10px; font-size: 12px; font-weight: 720; white-space: nowrap; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 11px 14px; border-bottom: 1px solid #edf1f5; text-align: left; font-size: 13px; vertical-align: top; }}
    th {{ background: #fafbfc; color: #475467; font-size: 12px; text-transform: uppercase; }}
    tr:hover td {{ background: #fbfcfd; }}
    .file-title {{ font-weight: 650; color: #172033; }}
    .summary {{ margin-top: 3px; color: #667085; max-width: 580px; }}
    .link {{ color: #1f6fb2; font-weight: 650; text-decoration: none; }}
    .empty {{ text-align: center; padding: 54px 20px; color: #667085; background: white; border: 1px solid #e2e8f0; border-radius: 8px; }}
    footer {{ color: #667085; text-align: center; padding: 22px; font-size: 13px; }}
    @media (max-width: 760px) {{
      .stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .toolbar {{ grid-template-columns: 1fr; }}
      th:nth-child(3), td:nth-child(3) {{ display: none; }}
      .day-head {{ align-items: flex-start; flex-direction: column; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="wrap">
      <div class="topline">
        <div>
          <h1>{safe_title}</h1>
          <p class="subtitle">PowerPoint files collected, deduplicated, and indexed for download.</p>
        </div>
        <nav class="actions">
          <a class="button" id="csvLink" href="metadata/documents.csv">Metadata CSV</a>
          <a class="button" id="jsonLink" href="metadata/documents.json">Metadata JSON</a>
        </nav>
      </div>
      <section class="stats">
        <div class="stat"><div class="number" id="totalFiles">0</div><div class="label">Total Files</div></div>
        <div class="stat"><div class="number" id="totalSize">0 B</div><div class="label">Total Size</div></div>
        <div class="stat"><div class="number" id="dayCount">0</div><div class="label">Collection Days</div></div>
        <div class="stat"><div class="number" id="progress">0%</div><div class="label">Target Progress</div></div>
      </section>
    </div>
  </header>
  <main>
    <div class="wrap">
      <div class="toolbar">
        <input id="filter" type="search" placeholder="Filter by title, category, source, or file type">
        <p class="muted" id="generatedAt">Loading archive...</p>
      </div>
      <section id="days"></section>
    </div>
  </main>
  <footer>{safe_title} &bull; Public archive page generated by PPT Hunter</footer>
  <script>
    const state = {{ manifest: null, query: "" }};
    const manifestUrl = new URL("portal_manifest.json", window.location.href);

    function formatNumber(value) {{
      return Number(value || 0).toLocaleString();
    }}
    function formatSize(bytes) {{
      const units = ["B", "KB", "MB", "GB", "TB"];
      let value = Number(bytes || 0);
      let unit = 0;
      while (value >= 1024 && unit < units.length - 1) {{ value /= 1024; unit += 1; }}
      return `${{value.toFixed(value >= 10 || unit === 0 ? 0 : 1)}} ${{units[unit]}}`;
    }}
    function escapeHtml(value) {{
      return String(value ?? "").replace(/[&<>"']/g, char => ({{ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }}[char]));
    }}
    function fileUrl(file) {{
      if (/^https?:\\/\\//.test(file.download_url || "")) return file.download_url;
      return new URL(file.download_url || file.key, window.location.href).href;
    }}
    function matches(file, query) {{
      if (!query) return true;
      const text = [file.title, file.file_type, file.category, file.summary, file.source_url, file.key].join(" ").toLowerCase();
      return text.includes(query.toLowerCase());
    }}
    function renderFile(file) {{
      return `<tr>
        <td>
          <div class="file-title">${{escapeHtml(file.title || file.key)}}</div>
          <div class="summary">${{escapeHtml(file.summary || file.source_url || "")}}</div>
        </td>
        <td>${{escapeHtml(String(file.file_type || "").toUpperCase())}}</td>
        <td>${{file.slides ? formatNumber(file.slides) + " slides" : escapeHtml(file.category || "")}}</td>
        <td>${{formatSize(file.size)}}</td>
        <td><a class="link" href="${{fileUrl(file)}}" download>Download</a></td>
        <td><a class="link" href="${{escapeHtml(file.source_url || "#")}}" target="_blank" rel="noopener">Source</a></td>
      </tr>`;
    }}
    function render() {{
      const manifest = state.manifest;
      const query = state.query.trim();
      if (!manifest) return;

      document.getElementById("totalFiles").textContent = formatNumber(manifest.total_files);
      document.getElementById("totalSize").textContent = formatSize(manifest.total_size);
      document.getElementById("dayCount").textContent = formatNumber((manifest.days || []).length);
      document.getElementById("progress").textContent = `${{Math.min(((manifest.total_files || 0) / (manifest.target_files || 1)) * 100, 100).toFixed(1)}}%`;
      document.getElementById("generatedAt").textContent = `Updated ${{new Date(manifest.generated_at).toLocaleString()}}`;
      document.getElementById("csvLink").href = new URL(manifest.metadata.csv_url, window.location.href).href;
      document.getElementById("jsonLink").href = new URL(manifest.metadata.json_url, window.location.href).href;

      const cards = (manifest.days || []).map(day => {{
        const files = (day.files || []).filter(file => matches(file, query));
        if (!files.length) return "";
        return `<article class="day">
          <div class="day-head">
            <div>
              <div class="day-title">${{escapeHtml(day.day)}}</div>
              <div class="day-meta">${{formatNumber(files.length)}} files &bull; ${{formatSize(files.reduce((sum, file) => sum + Number(file.size || 0), 0))}} &bull; ${{formatNumber(day.pptx_count)}} PPTX &bull; ${{formatNumber(day.ppt_count)}} PPT</div>
            </div>
            <span class="pill">${{formatNumber(day.file_count)}} collected</span>
          </div>
          <table>
            <thead><tr><th>File</th><th>Type</th><th>Info</th><th>Size</th><th>File</th><th>Source</th></tr></thead>
            <tbody>${{files.map(renderFile).join("")}}</tbody>
          </table>
        </article>`;
      }}).join("");

      document.getElementById("days").innerHTML = cards || '<div class="empty">No files match this filter yet.</div>';
    }}
    document.getElementById("filter").addEventListener("input", event => {{
      state.query = event.target.value;
      render();
    }});
    fetch(manifestUrl, {{ cache: "no-store" }})
      .then(response => response.ok ? response.json() : Promise.reject(new Error("Manifest unavailable")))
      .then(manifest => {{ state.manifest = manifest; render(); }})
      .catch(error => {{
        document.getElementById("generatedAt").textContent = error.message;
        document.getElementById("days").innerHTML = '<div class="empty">The archive manifest is not available yet.</div>';
      }});
  </script>
</body>
</html>
"""
