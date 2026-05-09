"use client";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, Loader2, AlertCircle, Sparkles } from "lucide-react";
import type { Job } from "@/lib/api";

const STAGES: Array<{ key: string; label: string }> = [
  { key: "queued", label: "排队" },
  { key: "extract_frames", label: "抽取关键帧" },
  { key: "detect_subjects", label: "YOLO 主体检测" },
  { key: "classify_sport", label: "运动类型识别" },
  { key: "detect_highlights", label: "高光时刻检测" },
  { key: "edit_video", label: "剪辑拼接成片" },
  { key: "generate_caption", label: "生成分享文案" },
  { key: "done", label: "完成" },
];

const order = (k: string) => STAGES.findIndex((s) => s.key === k);

export function ProgressView({ job }: { job: Job }) {
  const failed = job.stage === "failed";
  const current = order(job.stage);
  const pct = Math.max(4, Math.round(job.progress * 100));
  return (
    <motion.div
      initial={{ opacity: 0, y: 16, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 220, damping: 26 }}
      className="glass rounded-iosXl p-6"
    >
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2 text-[12.5px] text-secondary">
          <Sparkles className="h-3.5 w-3.5 text-accent" />
          任务 ID · <code className="text-tertiary">{job.id.slice(0, 8)}</code>
        </div>
        <div className="text-[14px] font-semibold tabular-nums tracking-tight">
          {failed ? (
            <span className="text-pink">失败</span>
          ) : job.stage === "done" ? (
            <span className="text-green">已完成</span>
          ) : (
            <span className="bg-gradient-to-r from-accent to-indigo bg-clip-text text-transparent">
              {pct}%
            </span>
          )}
        </div>
      </div>

      <div className="mb-5 h-1.5 overflow-hidden rounded-full bg-white/8">
        <motion.div
          initial={false}
          animate={{ width: `${pct}%` }}
          transition={{ type: "spring", stiffness: 120, damping: 22 }}
          className={`h-full rounded-full ${
            failed ? "bg-pink/70" : "shimmer-bar animate-shimmer"
          }`}
        />
      </div>

      <div className="mb-4 text-[14px] font-medium text-primary">{job.message}</div>

      <ol className="space-y-1.5">
        {STAGES.map((s, i) => {
          const status = failed
            ? i < current
              ? "done"
              : "pending"
            : i < current
            ? "done"
            : i === current
            ? "running"
            : "pending";
          return (
            <li key={s.key} className="flex items-center gap-2.5 text-[13.5px]">
              {status === "done" ? (
                <CheckCircle2 className="h-4 w-4 text-green" />
              ) : status === "running" ? (
                <Loader2 className="h-4 w-4 animate-spin text-accent" />
              ) : (
                <span className="h-4 w-4 rounded-full border border-white/15" />
              )}
              <span className={status === "pending" ? "text-tertiary" : "text-primary"}>
                {s.label}
              </span>
            </li>
          );
        })}
      </ol>

      <AnimatePresence>
        {failed && job.error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-5 flex items-start gap-2 rounded-ios border border-pink/30 bg-pink/10 p-3 text-[13px] text-pink/95"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <div className="break-words">{job.error}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
