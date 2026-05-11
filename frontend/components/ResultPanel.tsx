"use client";
import { motion } from "framer-motion";
import { Copy, Download, Share2, Sparkles, Check } from "lucide-react";
import { useState } from "react";
import type { Job } from "@/lib/api";
import { fileUrl } from "@/lib/api";

export function ResultPanel({ job }: { job: Job }) {
  const [copied, setCopied] = useState(false);
  const c = job.caption;
  const captionText = c
    ? `${c.title}\n\n${c.body}\n\n${(c.hashtags || []).join(" ")}`
    : "";

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 220, damping: 26 }}
      className="grid gap-5 md:grid-cols-5"
    >
      {/* 左：视频 */}
      <motion.div
        layout
        className="glass overflow-hidden rounded-iosXl md:col-span-3"
      >
        <video
          src={fileUrl(job.id, "highlight")}
          poster={job.thumbnail ? fileUrl(job.id, "thumbnail") : undefined}
          controls
          className="aspect-video w-full bg-black"
        />
        <div className="flex flex-wrap items-center justify-between gap-3 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-accent/30 bg-accent/15 px-3 py-1 text-[12px] font-medium text-accent">
              {job.sport_type ?? "通用运动"}
            </span>
            <span className="text-[11.5px] text-tertiary">
              置信度 {(job.sport_confidence * 100).toFixed(0)}% ·{" "}
              {job.highlights.length} 个高光
            </span>
          </div>
          <motion.a
            whileTap={{ scale: 0.95 }}
            href={fileUrl(job.id, "highlight")}
            download
            className="btn-ghost flex items-center gap-1.5 rounded-ios px-3 py-1.5 text-[13px]"
          >
            <Download className="h-3.5 w-3.5" />
            下载视频
          </motion.a>
        </div>
      </motion.div>

      {/* 右：文案 + 高光列表 */}
      <motion.div
        layout
        className="glass space-y-5 rounded-iosXl p-5 md:col-span-2"
      >
        <div className="flex items-center gap-2 text-[12.5px] text-secondary">
          <Share2 className="h-3.5 w-3.5 text-accent" />
          分享文案 · <span className="text-primary">{job.style}</span>
        </div>
        {c ? (
          <>
            <h3 className="font-display text-[19px] font-semibold leading-snug tracking-tight text-primary">
              {c.title}
            </h3>
            <p className="whitespace-pre-wrap text-[14.5px] leading-relaxed text-primary/95">
              {c.body}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {(c.hashtags || []).map((t) => (
                <span
                  key={t}
                  className="rounded-full border border-indigo/30 bg-indigo/15 px-2.5 py-0.5 text-[11.5px] font-medium text-indigo"
                >
                  {t}
                </span>
              ))}
            </div>
            <motion.button
              type="button"
              whileTap={{ scale: 0.95 }}
              onClick={async () => {
                await navigator.clipboard.writeText(captionText);
                setCopied(true);
                setTimeout(() => setCopied(false), 1600);
              }}
              className="btn-ghost flex items-center gap-2 rounded-ios px-3.5 py-2 text-[13.5px] font-medium"
            >
              {copied ? (
                <>
                  <Check className="h-4 w-4 text-green" />
                  已复制
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4" />
                  一键复制
                </>
              )}
            </motion.button>
          </>
        ) : (
          <p className="text-[13px] text-tertiary">文案生成中…</p>
        )}

        {job.highlights.length > 0 && (
          <div className="hairline pt-4">
            <div className="mb-2.5 flex items-center gap-2 text-[11.5px] uppercase tracking-[0.12em] text-tertiary">
              <Sparkles className="h-3 w-3" />
              高光时刻
            </div>
            <ul className="space-y-1.5">
              {job.highlights.map((h, i) => (
                <li
                  key={i}
                  className="flex items-start justify-between gap-3 text-[13px]"
                >
                  <div className="min-w-0">
                    <span className="text-primary">#{i + 1}</span>{" "}
                    <span className="text-secondary tabular-nums">
                      {h.start.toFixed(1)}s – {h.end.toFixed(1)}s
                    </span>
                    <div className="truncate text-[12px] text-tertiary">
                      {h.phrase || h.reason}
                    </div>
                  </div>
                  <span className="shrink-0 rounded-full bg-black/8 px-2 py-0.5 text-[11px] tabular-nums text-secondary">
                    {(h.score * 100).toFixed(0)}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </motion.div>
    </motion.div>
  );
}
