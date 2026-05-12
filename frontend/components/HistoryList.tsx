"use client";
import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState, useCallback } from "react";
import { Trash2, RefreshCcw, Film, Sparkles, Clock } from "lucide-react";
import { type Job, listJobs, deleteJob, fileUrl } from "@/lib/api";

type Props = {
  onPick: (job: Job) => void;
};

export function HistoryList({ onPick }: Props) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await listJobs();
      setJobs(list);
    } catch (e: any) {
      setError(e?.message ?? "加载历史失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const onDelete = async (id: string) => {
    if (!confirm("删除这条任务记录？仅从列表移除，源文件保留在磁盘。")) return;
    setDeleting(id);
    try {
      await deleteJob(id);
      setJobs((prev) => prev.filter((j) => j.id !== id));
    } catch (e: any) {
      setError(e?.message ?? "删除失败");
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-[12.5px] text-secondary">
          <Clock className="h-3.5 w-3.5 text-accent" />
          <span className="text-primary">生成记录</span>
          <span className="text-tertiary">· 共 {jobs.length} 条</span>
        </div>
        <button
          type="button"
          onClick={reload}
          disabled={loading}
          className="btn-ghost flex items-center gap-1.5 rounded-ios px-3 py-1.5 text-[12.5px]"
        >
          <RefreshCcw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          刷新
        </button>
      </div>

      {error && (
        <div className="rounded-ios border border-pink/30 bg-pink/10 px-3 py-2 text-[12.5px] text-pink">
          {error}
        </div>
      )}

      {!loading && jobs.length === 0 && (
        <div className="glass rounded-iosXl px-5 py-12 text-center text-[13px] text-tertiary">
          还没有生成记录。先去「当前任务」上传几条素材试试 ✂️
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <AnimatePresence initial={false}>
          {jobs.map((j) => (
            <motion.div
              key={j.id}
              layout
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.92 }}
              transition={{ type: "spring", stiffness: 300, damping: 28 }}
              className="glass group overflow-hidden rounded-iosXl"
            >
              <button
                type="button"
                onClick={() => onPick(j)}
                className="block w-full text-left"
              >
                <div className="relative aspect-video w-full bg-black/[0.06]">
                  {j.thumbnail ? (
                    <img
                      src={`${fileUrl(j.id, "thumbnail")}?v=${j.highlights.length}`}
                      alt={j.title ?? j.id}
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <div className="grid h-full place-items-center text-tertiary">
                      <Film className="h-7 w-7 opacity-40" />
                    </div>
                  )}
                  <div className="absolute left-2 top-2 flex flex-wrap items-center gap-1">
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10.5px] font-medium ${
                        j.mode === "compilation"
                          ? "bg-indigo/85 text-white"
                          : "bg-accent/85 text-white"
                      }`}
                    >
                      {j.mode === "compilation" ? "合集" : "短高光"}
                    </span>
                    {j.sport_type && (
                      <span className="rounded-full bg-black/55 px-2 py-0.5 text-[10.5px] font-medium text-white">
                        {j.sport_type}
                      </span>
                    )}
                  </div>
                  {j.stage !== "done" && j.stage !== "failed" && (
                    <div className="absolute inset-x-0 bottom-0 bg-black/60 px-2 py-1 text-[11px] text-white backdrop-blur">
                      {j.stage_label} · {(j.progress * 100).toFixed(0)}%
                    </div>
                  )}
                  {j.stage === "failed" && (
                    <div className="absolute inset-x-0 bottom-0 bg-pink/85 px-2 py-1 text-[11px] text-white">
                      失败：{j.error ?? "未知错误"}
                    </div>
                  )}
                </div>
                <div className="space-y-1 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="truncate font-display text-[14px] font-semibold tracking-tight text-primary">
                      {j.title ?? j.caption?.title ?? `任务 ${j.id.slice(0, 6)}`}
                    </div>
                    <span className="shrink-0 text-[11px] tabular-nums text-tertiary">
                      {formatDate(j.created_at)}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5 text-[11.5px] text-tertiary">
                    <span className="rounded-full bg-black/[0.06] px-2 py-0.5">
                      <Sparkles className="-mt-0.5 mr-1 inline h-2.5 w-2.5" />
                      {j.highlights.length} 段
                    </span>
                    <span className="rounded-full bg-black/[0.06] px-2 py-0.5">
                      {j.style}
                    </span>
                    {j.cover_date && (
                      <span className="rounded-full bg-black/[0.06] px-2 py-0.5">
                        {j.cover_date}
                      </span>
                    )}
                  </div>
                </div>
              </button>
              <div className="flex items-center justify-end gap-1 px-3 pb-3">
                <button
                  type="button"
                  onClick={() => onDelete(j.id)}
                  disabled={deleting === j.id}
                  className="grid h-7 w-7 place-items-center rounded-full text-tertiary transition hover:bg-pink/12 hover:text-pink"
                  title="从历史里删除"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}

function formatDate(ts: number): string {
  const d = new Date(ts * 1000);
  const now = new Date();
  const sameYear = d.getFullYear() === now.getFullYear();
  const opts: Intl.DateTimeFormatOptions = sameYear
    ? { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }
    : { year: "numeric", month: "numeric", day: "numeric" };
  return d.toLocaleString(undefined, opts);
}
