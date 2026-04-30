"use client";
import { Copy, Download, Share2 } from "lucide-react";
import { useState } from "react";
import type { Job } from "@/lib/api";
import { fileUrl } from "@/lib/api";

export function ResultPanel({ job }: { job: Job }) {
  const [copied, setCopied] = useState(false);
  const c = job.caption;
  const captionText = c ? `${c.title}\n\n${c.body}\n\n${(c.hashtags || []).join(" ")}` : "";

  return (
    <div className="grid gap-5 md:grid-cols-5">
      <div className="glass overflow-hidden rounded-2xl md:col-span-3">
        <video
          src={fileUrl(job.id, "highlight")}
          poster={job.thumbnail ? fileUrl(job.id, "thumbnail") : undefined}
          controls
          className="aspect-video w-full bg-black"
        />
        <div className="flex flex-wrap items-center justify-between gap-3 p-4">
          <div className="flex items-center gap-3">
            <span className="rounded-full border border-accent/30 bg-accent/10 px-2.5 py-0.5 text-xs">
              {job.sport_type ?? "通用运动"}
            </span>
            <span className="text-xs text-white/50">
              置信度 {(job.sport_confidence * 100).toFixed(0)}% · {job.highlights.length} 个高光
            </span>
          </div>
          <a
            href={fileUrl(job.id, "highlight")}
            download
            className="flex items-center gap-1.5 rounded-lg border border-line bg-white/[0.02] px-3 py-1.5 text-sm hover:border-accent/40"
          >
            <Download className="h-4 w-4" />
            下载视频
          </a>
        </div>
      </div>

      <div className="glass rounded-2xl p-5 md:col-span-2">
        <div className="mb-2 flex items-center gap-2 text-sm text-white/60">
          <Share2 className="h-4 w-4 text-accent2" />
          分享文案 · {job.style}
        </div>
        {c ? (
          <>
            <h3 className="mb-2 text-lg font-semibold leading-snug">{c.title}</h3>
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-white/85">{c.body}</p>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {(c.hashtags || []).map((t) => (
                <span
                  key={t}
                  className="rounded-full border border-accent2/30 bg-accent2/10 px-2 py-0.5 text-xs text-accent2"
                >
                  {t}
                </span>
              ))}
            </div>
            <button
              type="button"
              onClick={async () => {
                await navigator.clipboard.writeText(captionText);
                setCopied(true);
                setTimeout(() => setCopied(false), 1500);
              }}
              className="mt-4 flex items-center gap-1.5 rounded-lg border border-line bg-white/[0.02] px-3 py-1.5 text-sm hover:border-accent/40"
            >
              <Copy className="h-4 w-4" />
              {copied ? "已复制" : "一键复制"}
            </button>
          </>
        ) : (
          <p className="text-sm text-white/50">文案生成中…</p>
        )}

        {job.highlights.length > 0 && (
          <div className="mt-5">
            <div className="mb-2 text-xs uppercase tracking-wider text-white/40">高光时刻</div>
            <ul className="space-y-1.5">
              {job.highlights.map((h, i) => (
                <li key={i} className="flex items-start justify-between gap-3 text-sm">
                  <div className="min-w-0">
                    <span className="text-white/85">#{i + 1}</span>{" "}
                    <span className="text-white/60">
                      {h.start.toFixed(1)}s – {h.end.toFixed(1)}s
                    </span>
                    <div className="truncate text-xs text-white/50">{h.reason}</div>
                  </div>
                  <span className="shrink-0 rounded-full bg-white/5 px-2 py-0.5 text-xs text-white/70">
                    {(h.score * 100).toFixed(0)}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
