"use client";

import { ChevronDown, ChevronUp, Database, Download, FileArchive, Folder, Search } from "lucide-react";
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
  images: number | null;
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
  zip_url: string | null;
  files: ArchiveFile[];
};

type ArchiveManifest = {
  title: string;
  generated_at: string;
  target_files: number;
  total_files: number;
  total_size: number;
  zip_url: string | null;
  metadata: {
    csv_url: string;
  };
  days: ArchiveDay[];
};

type DayCard = ArchiveDay & {
  dayNumber: number;
  label: string;
  hasFiles: boolean;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
const CAMPAIGN_DAYS = 7;

export function PublicArchive() {
  const [manifest, setManifest] = useState<ArchiveManifest | null>(null);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [openDays, setOpenDays] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetch(`${API_BASE}/api/portal/manifest`, { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error("Archive is not available yet.");
        return response.json() as Promise<ArchiveManifest>;
      })
      .then((payload) => {
        setManifest(payload);
        const firstDay = payload.days.find((day) => day.file_count > 0);
        if (firstDay) setOpenDays(new Set([firstDay.day]));
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Archive is not available yet."));
  }, []);

  const dayCards = useMemo(() => buildDayCards(manifest?.days ?? []), [manifest]);
  const filteredDayCards = useMemo(() => {
    const cleanQuery = query.trim().toLowerCase();
    return dayCards.map((day) => ({
      ...day,
      files: day.files.filter((file) => matchesQuery(file, cleanQuery)),
    }));
  }, [dayCards, query]);

  const activeDays = dayCards.filter((day) => day.hasFiles).length;
  const remainingDays = Math.max(CAMPAIGN_DAYS - activeDays, 0);
  const target = manifest?.target_files ?? 200000;
  const totalFiles = manifest?.total_files ?? 0;
  const totalSize = manifest?.total_size ?? 0;
  const progress = Math.min((totalFiles / Math.max(target, 1)) * 100, 100);

  function toggleDay(day: string) {
    setOpenDays((current) => {
      const next = new Set(current);
      if (next.has(day)) next.delete(day);
      else next.add(day);
      return next;
    });
  }

  return (
    <main className="min-h-screen bg-[#eef1f4] px-4 py-4 text-[#111827] md:px-8">
      <section className="mx-auto max-w-6xl">
        <div className="grid gap-4 md:grid-cols-4">
          <Metric label="Total Files" value={formatNumber(totalFiles)} />
          <Metric label="Total Size" value={formatSize(totalSize)} />
          <Metric label="Days Active" value={formatNumber(activeDays)} />
          <Metric label="Days Remaining" value={formatNumber(remainingDays)} />
        </div>

        <section className="mt-5 rounded-lg bg-white px-5 py-4 shadow-sm ring-1 ring-black/5">
          <div className="mb-2 flex items-center justify-between gap-4 text-xs text-slate-700">
            <span>Progress toward {formatNumber(target)} file target</span>
            <span>
              {formatNumber(totalFiles)} / {formatNumber(target)} ({progress.toFixed(1)}%)
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-200">
            <div className="h-full rounded-full bg-[#0075d4]" style={{ width: `${Math.max(progress, totalFiles > 0 ? 0.5 : 0)}%` }} />
          </div>
        </section>

        <div className="mt-5 grid gap-3 md:grid-cols-[1fr_auto] md:items-center">
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Filter individual files"
              className="h-10 w-full rounded-lg border border-slate-200 bg-white pl-9 pr-3 text-sm shadow-sm outline-none focus:border-[#0075d4] focus:ring-2 focus:ring-[#0075d4]/15"
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <a className="inline-flex h-10 items-center gap-2 rounded-md bg-[#0075d4] px-3 text-sm font-semibold text-white hover:bg-[#0064b5]" href={resolveUrl(manifest?.zip_url ?? "/api/exports/documents.zip?limit=5000")}>
              <Download size={16} />
              Download All ZIP
            </a>
            <a className="inline-flex h-10 items-center gap-2 rounded-md bg-white px-3 text-sm font-semibold text-slate-700 shadow-sm ring-1 ring-black/5 hover:bg-slate-50" href={resolveUrl(manifest?.metadata.csv_url ?? "/api/exports/metadata.csv")}>
              <Database size={16} />
              CSV
            </a>
          </div>
        </div>

        <section className="mt-5 space-y-4">
          {filteredDayCards.map((day) => {
            const isOpen = openDays.has(day.day);
            return (
              <article key={day.day} className="overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-black/5">
                <button
                  type="button"
                  onClick={() => toggleDay(day.day)}
                  className="grid w-full grid-cols-[auto_1fr_auto] items-center gap-3 px-5 py-4 text-left"
                >
                  <span className={`rounded px-3 py-2 text-xs font-bold uppercase text-white ${day.hasFiles ? "bg-[#0075d4]" : "bg-[#060b27]"}`}>
                    Day {day.dayNumber}
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-semibold text-slate-950">
                      Day {day.dayNumber} - {day.label}
                    </span>
                    <span className="mt-1 block text-xs text-slate-500">
                      {day.hasFiles ? `${formatNumber(day.file_count)} files - ${formatSize(day.size)}` : "Collection not yet started"}
                    </span>
                  </span>
                  <span className="flex items-center gap-4 text-xs text-slate-600">
                    {day.hasFiles ? (
                      <>
                        <span>{formatNumber(day.pptx_count)} PPTX</span>
                        <span>{formatNumber(day.ppt_count)} PPT</span>
                      </>
                    ) : null}
                    {isOpen ? <ChevronUp className="text-slate-400" size={18} /> : <ChevronDown className="text-slate-400" size={18} />}
                  </span>
                </button>

                {isOpen && day.hasFiles ? (
                  <>
                    <section className="border-t border-slate-200 bg-slate-50 px-5 py-4">
                      <div className="mb-2 flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                          <FileArchive size={16} className="text-amber-600" />
                          ZIP Downloads
                        </div>
                        <a
                          className="inline-flex h-9 items-center gap-2 rounded-md bg-[#0075d4] px-3 text-xs font-semibold text-white hover:bg-[#0064b5]"
                          href={resolveUrl(day.zip_url ?? `/api/exports/documents.zip?day=${day.day}&limit=5000`)}
                        >
                          <Download size={15} />
                          Download ZIP
                        </a>
                      </div>
                      <p className="text-xs text-slate-500">ZIP files are prepared when requested. Large archives can take a moment to start.</p>
                    </section>

                    <section className="border-t border-slate-200">
                      <div className="flex items-center justify-between px-5 py-3 text-xs">
                        <div className="flex items-center gap-2 font-semibold text-[#0064b5]">
                          <Folder size={15} className="text-amber-500" />
                          Browse individual files ({formatNumber(day.files.length)} total)
                        </div>
                        <span className="font-semibold text-[#0064b5]">Show</span>
                      </div>
                      {day.files.length > 0 ? (
                        <div className="overflow-x-auto border-t border-slate-100">
                          <table className="w-full min-w-[740px] border-collapse text-left text-xs">
                            <thead>
                              <tr className="bg-slate-50 uppercase text-slate-500">
                                <th className="px-5 py-3">File</th>
                                <th className="px-3 py-3">Type</th>
                                <th className="px-3 py-3">Size</th>
                                <th className="px-3 py-3">File</th>
                                <th className="px-3 py-3">Source</th>
                              </tr>
                            </thead>
                            <tbody>
                              {day.files.map((file) => (
                                <tr key={file.id} className="border-t border-slate-100 hover:bg-slate-50">
                                  <td className="px-5 py-3">
                                    <p className="line-clamp-1 font-semibold text-slate-900">{file.title}</p>
                                    <p className="mt-1 line-clamp-1 text-slate-500">{file.summary || file.source_url}</p>
                                  </td>
                                  <td className="px-3 py-3 font-semibold uppercase text-slate-600">{file.file_type}</td>
                                  <td className="px-3 py-3 text-slate-600">
                                    {formatSize(file.size)}
                                    {file.images !== null ? <span className="ml-2 text-slate-400">{formatNumber(file.images)} images</span> : null}
                                  </td>
                                  <td className="px-3 py-3">
                                    <a className="font-semibold text-[#0064b5] hover:text-[#004f91]" href={resolveUrl(file.download_url)}>
                                      Download
                                    </a>
                                  </td>
                                  <td className="px-3 py-3">
                                    <a className="font-semibold text-[#0064b5] hover:text-[#004f91]" href={file.source_url} target="_blank" rel="noopener">
                                      Source
                                    </a>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <div className="border-t border-slate-100 px-5 py-5 text-xs text-slate-500">No files match this filter.</div>
                      )}
                    </section>
                  </>
                ) : null}
              </article>
            );
          })}
        </section>

        {error ? <div className="mt-5 rounded-lg bg-white px-5 py-10 text-center text-sm text-slate-500 shadow-sm ring-1 ring-black/5">{error}</div> : null}
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-white px-6 py-5 text-center shadow-sm ring-1 ring-black/5">
      <p className="text-3xl font-bold text-[#0075d4]">{value}</p>
      <p className="mt-2 text-[10px] font-semibold uppercase text-slate-500">{label}</p>
    </div>
  );
}

function buildDayCards(days: ArchiveDay[]) {
  const byDay = new Map(days.map((day) => [day.day, day]));
  const earliest = days.length > 0 ? parseDate(days.map((day) => day.day).sort()[0]) : new Date();
  const cards: DayCard[] = [];

  for (let index = 0; index < CAMPAIGN_DAYS; index += 1) {
    const date = new Date(earliest);
    date.setDate(earliest.getDate() + index);
    const key = toDateKey(date);
    const existing = byDay.get(key);
    cards.push({
      day: key,
      dayNumber: index + 1,
      label: formatDayLabel(date),
      file_count: existing?.file_count ?? 0,
      size: existing?.size ?? 0,
      ppt_count: existing?.ppt_count ?? 0,
      pptx_count: existing?.pptx_count ?? 0,
      zip_url: existing?.zip_url ?? `/api/exports/documents.zip?day=${key}&limit=5000`,
      files: existing?.files ?? [],
      hasFiles: Boolean(existing && existing.file_count > 0),
    });
  }

  const active = cards.filter((day) => day.hasFiles);
  const inactive = cards.filter((day) => !day.hasFiles);
  return [...active, ...inactive];
}

function parseDate(value: string) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function toDateKey(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatDayLabel(date: Date) {
  return new Intl.DateTimeFormat("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  }).format(date);
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
