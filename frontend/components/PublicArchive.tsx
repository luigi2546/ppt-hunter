"use client";

import { Database, Download, FileText, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

type ArchiveFile = {
  id: string;
  title: string;
  key: string;
  download_url: string;
  source_url: string;
  file_type: string;
  size: number;
  slides: number | null;
  category: string | null;
  summary: string | null;
  sha256: string | null;
  updated_at: string | null;
};

type ArchiveDay = {
  day: string;
  file_count: number;
  size: number;
  ppt_count: number;
  pptx_count: number;
  files: ArchiveFile[];
};

type ArchiveManifest = {
  title: string;
  generated_at: string;
  target_files: number;
  total_files: number;
  total_size: number;
  metadata: {
    csv_url: string;
    json_url: string;
  };
  days: ArchiveDay[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

export function PublicArchive() {
  const [manifest, setManifest] = useState<ArchiveManifest | null>(null);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/portal/manifest`, { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error("Archive is not available yet.");
        return response.json() as Promise<ArchiveManifest>;
      })
      .then(setManifest)
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Archive is not available yet."));
  }, []);

  const filteredDays = useMemo(() => {
    if (!manifest) return [];
    const cleanQuery = query.trim().toLowerCase();
    return manifest.days
      .map((day) => ({
        ...day,
        files: day.files.filter((file) => matchesQuery(file, cleanQuery)),
      }))
      .filter((day) => day.files.length > 0);
  }, [manifest, query]);

  const title = manifest?.title ?? "Research Document Archive";
  const progress = manifest ? Math.min((manifest.total_files / Math.max(manifest.target_files, 1)) * 100, 100) : 0;

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <header className="bg-[linear-gradient(135deg,#0f5132,#1f7a5a_55%,#234c75)] text-white">
        <div className="mx-auto max-w-7xl px-5 py-8">
          <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
            <div>
              <h1 className="text-4xl font-bold tracking-normal md:text-5xl">{title}</h1>
              <p className="mt-2 text-sm text-white/80">PowerPoint files collected, deduplicated, and indexed for download.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <a
                className="inline-flex h-10 items-center gap-2 rounded border border-white/25 bg-white/15 px-3 text-sm font-semibold text-white hover:bg-white/20"
                href={resolveUrl(manifest?.metadata.csv_url ?? "/api/exports/metadata")}
              >
                <Database size={16} />
                Metadata CSV
              </a>
              <a
                className="inline-flex h-10 items-center gap-2 rounded border border-white/25 bg-white/15 px-3 text-sm font-semibold text-white hover:bg-white/20"
                href={resolveUrl(manifest?.metadata.json_url ?? "/api/exports/metadata")}
              >
                <FileText size={16} />
                Metadata JSON
              </a>
            </div>
          </div>

          <section className="mt-7 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Metric label="Total Files" value={formatNumber(manifest?.total_files ?? 0)} />
            <Metric label="Total Size" value={formatSize(manifest?.total_size ?? 0)} />
            <Metric label="Collection Days" value={formatNumber(manifest?.days.length ?? 0)} />
            <Metric label="Target Progress" value={`${progress.toFixed(1)}%`} />
          </section>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-5 py-6">
        <div className="mb-5 grid gap-3 md:grid-cols-[1fr_auto] md:items-center">
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Filter by title, category, source, or file type"
              className="h-11 w-full rounded border border-slate-300 bg-white pl-10 pr-3 text-sm outline-none focus:border-emerald-700 focus:ring-2 focus:ring-emerald-700/15"
            />
          </label>
          <p className="text-sm text-slate-500">
            {manifest ? `Updated ${new Date(manifest.generated_at).toLocaleString()}` : error || "Loading archive..."}
          </p>
        </div>

        <div className="space-y-4">
          {filteredDays.map((day) => (
            <article key={day.day} className="overflow-hidden rounded border border-slate-200 bg-white shadow-sm">
              <div className="flex flex-col gap-3 border-b border-slate-200 px-5 py-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <h2 className="text-lg font-bold">{day.day}</h2>
                  <p className="mt-1 text-sm text-slate-500">
                    {formatNumber(day.files.length)} files - {formatSize(sumSize(day.files))} - {formatNumber(day.pptx_count)} PPTX -{" "}
                    {formatNumber(day.ppt_count)} PPT
                  </p>
                </div>
                <span className="w-fit rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-800">
                  {formatNumber(day.file_count)} collected
                </span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] border-collapse text-left text-sm">
                  <thead>
                    <tr className="bg-slate-50 text-xs uppercase text-slate-500">
                      <th className="px-4 py-3">File</th>
                      <th className="px-4 py-3">Type</th>
                      <th className="px-4 py-3">Info</th>
                      <th className="px-4 py-3">Size</th>
                      <th className="px-4 py-3">Download</th>
                      <th className="px-4 py-3">Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {day.files.map((file) => (
                      <tr key={file.id} className="border-t border-slate-100 hover:bg-slate-50">
                        <td className="px-4 py-3">
                          <p className="font-semibold text-slate-950">{file.title}</p>
                          <p className="mt-1 line-clamp-2 max-w-2xl text-xs text-slate-500">{file.summary || file.source_url}</p>
                        </td>
                        <td className="px-4 py-3 font-semibold uppercase text-slate-600">{file.file_type}</td>
                        <td className="px-4 py-3 text-slate-600">{file.slides ? `${formatNumber(file.slides)} slides` : file.category || ""}</td>
                        <td className="px-4 py-3 text-slate-600">{formatSize(file.size)}</td>
                        <td className="px-4 py-3">
                          <a
                            className="inline-flex h-9 items-center gap-2 rounded bg-slate-900 px-3 text-xs font-semibold text-white hover:bg-slate-700"
                            href={resolveUrl(file.download_url)}
                          >
                            <Download size={15} />
                            File
                          </a>
                        </td>
                        <td className="px-4 py-3">
                          <a className="font-semibold text-blue-700 hover:text-blue-900" href={file.source_url} target="_blank" rel="noopener">
                            Source
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </article>
          ))}
        </div>

        {manifest && filteredDays.length === 0 ? (
          <div className="rounded border border-slate-200 bg-white px-5 py-14 text-center text-slate-500">No files match this filter yet.</div>
        ) : null}
        {error ? <div className="rounded border border-slate-200 bg-white px-5 py-14 text-center text-slate-500">{error}</div> : null}
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-white/20 bg-white/15 px-4 py-4">
      <p className="text-3xl font-bold">{value}</p>
      <p className="mt-1 text-xs text-white/75">{label}</p>
    </div>
  );
}

function matchesQuery(file: ArchiveFile, query: string) {
  if (!query) return true;
  return [file.title, file.file_type, file.category, file.summary, file.source_url, file.key].join(" ").toLowerCase().includes(query);
}

function resolveUrl(url: string) {
  if (!url) return "#";
  if (/^https?:\/\//.test(url)) return url;
  return `${API_BASE}${url.startsWith("/") ? url : `/${url}`}`;
}

function sumSize(files: ArchiveFile[]) {
  return files.reduce((total, file) => total + Number(file.size || 0), 0);
}

function formatNumber(value: number) {
  return value.toLocaleString();
}

function formatSize(bytes: number) {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = Number(bytes || 0);
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(value >= 10 || unit === 0 ? 0 : 1)} ${units[unit]}`;
}
