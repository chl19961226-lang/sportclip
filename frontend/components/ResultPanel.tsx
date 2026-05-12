"use client";
import { motion } from "framer-motion";
import { Copy, Download, Share2, Check } from "lucide-react";
import { useState } from "react";
import type { Job } from "@/lib/api";
import { fileUrl } from "@/lib/api";
import { HighlightReorder } from "./HighlightReorder";

export function ResultPanel({
  job,
  onJobChange,
}: {
  job: Job;
  onJobChange: (j: Job) => void;
}) {
  const [copied, setCopied] = useState(false);
  const c = job.caption;
  const captionText = c
    ? `${c.title}\n\n${c.body}\n\n${(c.hashtags || []).join(" ")}`
    : "";
  // 重剪后视频文件被覆盖、URL 不变；用 highlights 指纹做 cache buster 强制重拉
  const cacheKey = `${job.highlights.length}-${job.highlights[0]?.start ?? 0}-${
    job.highlights[0]?.score ?? 0
  }`;

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
        className="glass relative overflow-hidden rounded-iosXl md:col-span-3"
      >
        <video
          key={cacheKey}
          src={`${fileUrl(job.id, "highlight")}?v=${cacheKey}`}
          poster={job.thumbnail ? `${fileUrl(job.id, "thumbnail")}?v=${cacheKey}` : undefined}
          controls
          className="aspect-video w-full bg-black"
        />
        {job.stage !== "done" && job.stage !== "failed" && (
          <div className="pointer-events-none absolute inset-x-0 top-0 flex items-center justify-center gap-2 bg-black/55 px-3 py-1.5 text-[12.5px] text-white backdrop-blur-md">
            <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-white" />
            <span>{job.message || job.stage_label || "处理中…"}</span>
          </div>
        )}
        <div className="flex flex-wrap items-center justify-between gap-3 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-indigo/30 bg-indigo/12 px-3 py-1 text-[12px] font-medium text-indigo">
              {job.mode === "compilation" ? "合集长片" : "短高光"}
            </span>
            <span className="rounded-full border border-accent/30 bg-accent/15 px-3 py-1 text-[12px] font-medium text-accent">
              {job.sport_type ?? "通用运动"}
            </span>
            {job.mode === "compilation" && job.title && (
              <span className="rounded-full border border-line2 bg-black/[0.04] px-3 py-1 text-[12px] text-secondary">
                {job.title}
                {job.cover_date ? ` · ${job.cover_date}` : ""}
              </span>
            )}
            <span className="text-[11.5px] text-tertiary">
              置信度 {(job.sport_confidence * 100).toFixed(0)}% ·{" "}
              {job.highlights.length} 段被剪入
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
            <HighlightReorder job={job} onJobChange={onJobChange} />
          </div>
        )}
      </motion.div>
    </motion.div>
  );
}
