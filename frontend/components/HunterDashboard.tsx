"use client";

import { Download, FileSearch, Link as LinkIcon, Loader2, RefreshCw, ShieldCheck } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

type DocumentItem = {
  id: string;
  title: string;
  source_url: string;
  provider: string;
  file_type: string;
  status: string;
  description: string | null;
  size_bytes: number | null;
  slide_count: number | null;
  category: string | null;
  confidence: number | null;
  summary: string | null;
};

type ManualLinksResult = {
  created: number;
  existing: number;
  queued: number;
  skipped: number;
  invalid: string[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

export function HunterDashboard() {
  const [linksText, setLinksText] = useState("");
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [bulkLoading, setBulkLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const readyCount = useMemo(() => documents.filter((doc) => doc.status === "ready").length, [documents]);
  const downloadableCount = useMemo(
    () => documents.filter((doc) => ["discovered", "download_failed"].includes(doc.status)).length,
    [documents],
  );
  const activeDownloadCount = useMemo(
    () => documents.filter((doc) => ["download_queued", "downloading"].includes(doc.status)).length,
    [documents],
  );
  const exportableCount = useMemo(() => documents.filter((doc) => doc.size_bytes !== null).length, [documents]);

  async function fetchDocuments() {
    const response = await fetch(`${API_BASE}/api/documents?limit=500`, { cache: "no-store" });
    if (!response.ok) return [];
    return (await response.json()) as DocumentItem[];
  }

  async function refresh() {
    setDocuments(await fetchDocuments());
  }

  useEffect(() => {
    refresh().catch(() => setMessage("Backend is not reachable yet."));
    const timer = window.setInterval(() => refresh().catch(() => undefined), 5000);
    return () => window.clearInterval(timer);
  }, []);

  async function submitLinks(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const urls = parseLinks(linksText);
    if (urls.length === 0) {
      setMessage("Add at least one PPT or PPTX URL.");
      return;
    }

    setLoading(true);
    setMessage(null);
    try {
      const response = await fetch(`${API_BASE}/api/documents/manual-links`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ urls }),
      });
      if (!response.ok) throw new Error(await response.text());
      const result = (await response.json()) as ManualLinksResult;
      setMessage(formatManualLinksMessage(result));
      setLinksText("");
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to add links.");
    } finally {
      setLoading(false);
    }
  }

  async function queueDownload(documentId: string) {
    await fetch(`${API_BASE}/api/documents/${documentId}/download`, { method: "POST" });
    await refresh();
  }

  async function toggleSelected(document: DocumentItem, checked: boolean) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (checked) next.add(document.id);
      else next.delete(document.id);
      return next;
    });

    if (checked && ["discovered", "download_failed"].includes(document.status)) {
      setMessage(`Queued ${document.title}.`);
      await queueDownload(document.id);
    }
  }

  async function queueAllDownloads() {
    setBulkLoading(true);
    setMessage(null);
    try {
      const response = await fetch(`${API_BASE}/api/documents/download-all`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ limit: 500 }),
      });
      if (!response.ok) throw new Error(await response.text());
      const result = await response.json();
      let latestDocs = await fetchDocuments();
      setDocuments(latestDocs);
      setMessage(`${result.queued} downloads queued. Preparing ZIP...`);

      for (let attempt = 0; attempt < 180; attempt += 1) {
        const active = latestDocs.filter((doc) => ["download_queued", "downloading"].includes(doc.status)).length;
        if (active === 0) break;
        setMessage(`${active} downloads still running. Preparing ZIP...`);
        await wait(5000);
        latestDocs = await fetchDocuments();
        setDocuments(latestDocs);
      }

      const link = document.createElement("a");
      link.href = `${API_BASE}/api/exports/documents.zip?limit=500&download=${Date.now()}`;
      link.download = "ppt-hunter-export.zip";
      document.body.appendChild(link);
      link.click();
      link.remove();
      setMessage("ZIP download started.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to prepare ZIP download.");
    } finally {
      setBulkLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-neutral-950 text-neutral-100">
      <section className="border-b border-neutral-800 bg-neutral-900">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 px-5 py-6 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded bg-emerald-500 text-neutral-950">
              <FileSearch size={22} />
            </div>
            <div>
              <h1 className="text-2xl font-semibold tracking-normal">PPT Hunter</h1>
              <p className="text-sm text-neutral-400">Link-based deck collection and dedupe.</p>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3 text-sm">
            <Metric label="Documents" value={documents.length.toString()} />
            <Metric label="Ready" value={readyCount.toString()} />
            <Metric label="Selected" value={selectedIds.size.toString()} />
          </div>
        </div>
      </section>

      <div className="mx-auto grid max-w-7xl gap-6 px-5 py-6 lg:grid-cols-[360px_1fr]">
        <aside className="space-y-4">
          <form onSubmit={submitLinks} className="rounded border border-neutral-800 bg-neutral-900 p-4">
            <label className="text-sm font-medium text-neutral-300" htmlFor="links">
              PPT/PPTX links
            </label>
            <textarea
              id="links"
              value={linksText}
              onChange={(event) => setLinksText(event.target.value)}
              placeholder="https://example.com/deck.pptx"
              className="mt-2 min-h-44 w-full resize-none rounded border border-neutral-700 bg-neutral-950 p-3 text-sm outline-none ring-emerald-500 focus:ring-2"
            />
            <button
              className="mt-4 flex h-11 w-full items-center justify-center gap-2 rounded bg-emerald-500 px-4 text-sm font-semibold text-neutral-950 hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={loading}
            >
              {loading ? <Loader2 className="animate-spin" size={18} /> : <LinkIcon size={18} />}
              Add links + download
            </button>
            {message ? <p className="mt-3 text-sm text-neutral-400">{message}</p> : null}
          </form>

          <section className="rounded border border-neutral-800 bg-neutral-900 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-neutral-200">Link queue</h2>
              <button onClick={refresh} className="rounded p-2 text-neutral-400 hover:bg-neutral-800 hover:text-neutral-100" title="Refresh">
                <RefreshCw size={16} />
              </button>
            </div>
            <div className="space-y-3">
              {documents.slice(0, 8).map((document) => (
                <button
                  key={document.id}
                  type="button"
                  onClick={() => toggleSelected(document, !selectedIds.has(document.id))}
                  className="block w-full border-t border-neutral-800 pt-3 text-left first:border-t-0 first:pt-0"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="line-clamp-1 text-sm text-neutral-200">{document.title}</p>
                    <Status value={document.status} />
                  </div>
                  <p className="mt-1 text-xs text-neutral-500">{document.provider}</p>
                </button>
              ))}
              {documents.length === 0 ? <p className="text-sm text-neutral-500">No links added yet.</p> : null}
            </div>
          </section>
        </aside>

        <section className="rounded border border-neutral-800 bg-neutral-900">
          <div className="flex flex-col gap-4 border-b border-neutral-800 p-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-base font-semibold">Document queue</h2>
              <p className="text-sm text-neutral-500">Added links move through download, extraction, and enrichment.</p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={queueAllDownloads}
                className="flex items-center gap-2 rounded bg-neutral-100 px-3 py-2 text-sm font-medium text-neutral-950 hover:bg-white disabled:cursor-not-allowed disabled:opacity-50"
                disabled={bulkLoading || (downloadableCount === 0 && exportableCount === 0)}
              >
                {bulkLoading ? <Loader2 className="animate-spin" size={16} /> : <Download size={16} />}
                Queue all + ZIP ({downloadableCount || activeDownloadCount || exportableCount})
              </button>
              <ShieldCheck className="text-emerald-400" size={22} />
            </div>
          </div>

          <div className="divide-y divide-neutral-800">
            {documents.map((document) => (
              <article key={document.id} className="grid gap-4 p-4 md:grid-cols-[1fr_auto]">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(document.id)}
                      onChange={(event) => toggleSelected(document, event.target.checked)}
                      className="h-4 w-4 accent-emerald-500"
                      aria-label={`Select ${document.title}`}
                    />
                    <h3 className="font-medium text-neutral-100">{document.title}</h3>
                    <span className="rounded bg-neutral-800 px-2 py-1 text-xs uppercase text-neutral-400">{document.file_type}</span>
                    <Status value={document.status} />
                  </div>
                  <p className="mt-2 line-clamp-2 text-sm text-neutral-400">{document.summary || document.description || document.source_url}</p>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-neutral-500">
                    <span>{document.provider}</span>
                    {document.category ? <span>{document.category}</span> : null}
                    {document.slide_count ? <span>{document.slide_count} slides</span> : null}
                    {document.size_bytes ? <span>{Math.round(document.size_bytes / 1024)} KB</span> : null}
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <a className="rounded border border-neutral-700 px-3 py-2 text-sm text-neutral-300 hover:bg-neutral-800" href={document.source_url} target="_blank">
                    Source
                  </a>
                  <button
                    onClick={() => queueDownload(document.id)}
                    className="flex items-center gap-2 rounded bg-neutral-100 px-3 py-2 text-sm font-medium text-neutral-950 hover:bg-white disabled:opacity-50"
                    disabled={!["discovered", "download_failed"].includes(document.status)}
                  >
                    <Download size={16} />
                    Queue
                  </button>
                </div>
              </article>
            ))}
            {documents.length === 0 ? <p className="p-6 text-sm text-neutral-500">No links added yet.</p> : null}
          </div>
        </section>
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-neutral-800 bg-neutral-950 px-4 py-3">
      <p className="text-xs text-neutral-500">{label}</p>
      <p className="text-xl font-semibold">{value}</p>
    </div>
  );
}

function Status({ value }: { value: string }) {
  const className =
    value === "ready" || value === "completed"
      ? "bg-emerald-500/15 text-emerald-300"
      : value.includes("fail")
        ? "bg-red-500/15 text-red-300"
        : "bg-amber-500/15 text-amber-300";
  return <span className={`rounded px-2 py-1 text-xs ${className}`}>{value.replace("_", " ")}</span>;
}

function parseLinks(text: string) {
  return Array.from(
    new Set(
      text
        .split(/[\s,]+/)
        .map((part) => part.trim())
        .filter(Boolean),
    ),
  );
}

function formatManualLinksMessage(result: ManualLinksResult) {
  const parts = [
    `${result.queued} queued`,
    `${result.created} new`,
    `${result.existing} duplicates`,
    `${result.skipped} already active`,
  ];
  if (result.invalid.length > 0) parts.push(`${result.invalid.length} invalid`);
  return parts.join(" - ");
}

function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
