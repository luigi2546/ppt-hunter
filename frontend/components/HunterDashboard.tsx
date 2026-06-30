"use client";

import { Download, FileSearch, Loader2, RefreshCw, ShieldCheck, Sparkles } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

type SearchRun = {
  id: string;
  query: string;
  provider: string;
  status: string;
  result_count: number;
  error: string | null;
  created_at: string;
};

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

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

export function HunterDashboard() {
  const [query, setQuery] = useState("artificial intelligence strategy");
  const [provider, setProvider] = useState("all");
  const [runs, setRuns] = useState<SearchRun[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [bulkLoading, setBulkLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

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
    const [runsResponse, docs] = await Promise.all([
      fetch(`${API_BASE}/api/search-runs`, { cache: "no-store" }),
      fetchDocuments(),
    ]);
    if (runsResponse.ok) setRuns(await runsResponse.json());
    setDocuments(docs);
  }

  useEffect(() => {
    refresh().catch(() => setMessage("Backend is not reachable yet."));
    const timer = window.setInterval(() => refresh().catch(() => undefined), 5000);
    return () => window.clearInterval(timer);
  }, []);

  async function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setMessage(null);
    try {
      const response = await fetch(`${API_BASE}/api/search-runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, provider, limit: 500, auto_download: true }),
      });
      if (!response.ok) throw new Error(await response.text());
      setMessage("Discovery and downloads queued.");
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to queue discovery.");
    } finally {
      setLoading(false);
    }
  }

  async function queueDownload(documentId: string) {
    await fetch(`${API_BASE}/api/documents/${documentId}/download`, { method: "POST" });
    await refresh();
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
          <div>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded bg-emerald-500 text-neutral-950">
                <FileSearch size={22} />
              </div>
              <div>
                <h1 className="text-2xl font-semibold tracking-normal">PPT Hunter</h1>
                <p className="text-sm text-neutral-400">Public deck discovery, extraction, and AI triage.</p>
              </div>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3 text-sm">
            <Metric label="Documents" value={documents.length.toString()} />
            <Metric label="Ready" value={readyCount.toString()} />
            <Metric label="Runs" value={runs.length.toString()} />
          </div>
        </div>
      </section>

      <div className="mx-auto grid max-w-7xl gap-6 px-5 py-6 lg:grid-cols-[360px_1fr]">
        <aside className="space-y-4">
          <form onSubmit={submitSearch} className="rounded border border-neutral-800 bg-neutral-900 p-4">
            <label className="text-sm font-medium text-neutral-300" htmlFor="query">
              Discovery query
            </label>
            <textarea
              id="query"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="mt-2 min-h-28 w-full resize-none rounded border border-neutral-700 bg-neutral-950 p-3 text-sm outline-none ring-emerald-500 focus:ring-2"
            />
            <label className="mt-4 block text-sm font-medium text-neutral-300" htmlFor="provider">
              Provider
            </label>
            <select
              id="provider"
              value={provider}
              onChange={(event) => setProvider(event.target.value)}
              className="mt-2 w-full rounded border border-neutral-700 bg-neutral-950 p-3 text-sm outline-none ring-emerald-500 focus:ring-2"
            >
              <option value="auto">Auto</option>
              <option value="all">All configured sources</option>
              <option value="brave">Brave</option>
              <option value="internet_archive">Internet Archive</option>
              <option value="google">Google via DataForSEO</option>
              <option value="bing">Bing via DataForSEO</option>
              <option value="duckduckgo">DuckDuckGo via DataForSEO</option>
              <option value="mock">Mock</option>
            </select>
            <button
              className="mt-4 flex h-11 w-full items-center justify-center gap-2 rounded bg-emerald-500 px-4 text-sm font-semibold text-neutral-950 hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={loading}
            >
              {loading ? <Loader2 className="animate-spin" size={18} /> : <Sparkles size={18} />}
              Find 500 + download all
            </button>
            {message ? <p className="mt-3 text-sm text-neutral-400">{message}</p> : null}
          </form>

          <section className="rounded border border-neutral-800 bg-neutral-900 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-neutral-200">Recent runs</h2>
              <button onClick={refresh} className="rounded p-2 text-neutral-400 hover:bg-neutral-800 hover:text-neutral-100" title="Refresh">
                <RefreshCw size={16} />
              </button>
            </div>
            <div className="space-y-3">
              {runs.map((run) => (
                <div key={run.id} className="border-t border-neutral-800 pt-3 first:border-t-0 first:pt-0">
                  <div className="flex items-center justify-between gap-3">
                    <p className="line-clamp-1 text-sm text-neutral-200">{run.query}</p>
                    <Status value={run.status} />
                  </div>
                  <p className="mt-1 text-xs text-neutral-500">
                    {run.provider} - {run.result_count} new
                  </p>
                </div>
              ))}
              {runs.length === 0 ? <p className="text-sm text-neutral-500">No discovery runs yet.</p> : null}
            </div>
          </section>
        </aside>

        <section className="rounded border border-neutral-800 bg-neutral-900">
          <div className="flex flex-col gap-4 border-b border-neutral-800 p-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-base font-semibold">Document queue</h2>
              <p className="text-sm text-neutral-500">Discovered decks move through download, extraction, and enrichment.</p>
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
            {documents.length === 0 ? <p className="p-6 text-sm text-neutral-500">No decks discovered yet.</p> : null}
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

function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
