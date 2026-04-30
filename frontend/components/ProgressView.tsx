"use client";
import { CheckCircle2, Loader2, AlertCircle } from "lucide-react";
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
  return (
    <div className="glass rounded-2xl p-5">
      <div className="mb-3 flex items-center justify-between">
        <div className="text-sm text-white/70">任务 ID · {job.id}</div>
        <div className="text-sm">
          {failed ? (
            <span className="text-red-400">失败</span>
          ) : job.stage === "done" ? (
            <span className="text-emerald-400">完成</span>
          ) : (
            <span className="text-accent2">{Math.round(job.progress * 100)}%</span>
          )}
        </div>
      </div>

      <div className="mb-4 h-2 overflow-hidden rounded-full bg-white/5">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            failed ? "bg-red-500/60" : "shimmer-bar animate-shimmer"
          }`}
          style={{ width: `${Math.max(4, Math.round(job.progress * 100))}%` }}
        />
      </div>

      <div className="mb-3 text-sm text-white/80">{job.message}</div>

      <ol className="space-y-1.5">
        {STAGES.map((s, i) => {
          const status = failed
            ? "pending"
            : i < current
            ? "done"
            : i === current
            ? "running"
            : "pending";
          return (
            <li key={s.key} className="flex items-center gap-2 text-sm">
              {status === "done" ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              ) : status === "running" ? (
                <Loader2 className="h-4 w-4 animate-spin text-accent2" />
              ) : (
                <span className="h-4 w-4 rounded-full border border-white/20" />
              )}
              <span className={status === "pending" ? "text-white/40" : "text-white/85"}>
                {s.label}
              </span>
            </li>
          );
        })}
      </ol>

      {failed && job.error && (
        <div className="mt-4 flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
          <AlertCircle className="mt-0.5 h-4 w-4" />
          <div>{job.error}</div>
        </div>
      )}
    </div>
  );
}
