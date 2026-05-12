"use client";
import { Reorder, motion, AnimatePresence } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import { GripVertical, Trash2, RotateCcw, Check } from "lucide-react";
import {
  type Job,
  type Highlight,
  type ReorderItem,
  reorderJob,
} from "@/lib/api";

type Props = {
  job: Job;
  onJobChange: (j: Job) => void;
};

// 给每个高光段做一个稳定 key，便于 Reorder 跟踪
function keyOf(h: Highlight): string {
  return `${h.src}__${h.start.toFixed(3)}__${h.end.toFixed(3)}`;
}

export function HighlightReorder({ job, onJobChange }: Props) {
  // 本地草稿：未点"应用"前可以随便拖 / 删
  const [items, setItems] = useState<Highlight[]>(job.highlights);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // 整体 busy = 本地正在提交 OR 后端在重剪中（job 还没到 done/failed）
  const jobBusy = job.stage !== "done" && job.stage !== "failed";
  const busy = submitting || jobBusy;

  // job 变化时（外部 setJob，比如重剪 / 重排序完成）重置草稿
  useEffect(() => {
    setItems(job.highlights);
    setError(null);
  }, [job.id, job.highlights]);

  const dirty = useMemo(() => {
    if (items.length !== job.highlights.length) return true;
    for (let i = 0; i < items.length; i++) {
      if (keyOf(items[i]) !== keyOf(job.highlights[i])) return true;
    }
    return false;
  }, [items, job.highlights]);

  const reset = () => setItems(job.highlights);

  const remove = (h: Highlight) => {
    setItems((prev) => prev.filter((x) => keyOf(x) !== keyOf(h)));
  };

  const apply = async () => {
    if (!dirty) return;
    if (items.length === 0) {
      setError("至少保留一段，不能全删");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const order: ReorderItem[] = items.map((h) => ({
        src: h.src,
        start: h.start,
        end: h.end,
      }));
      const next = await reorderJob(job.id, order);
      // 把 job 灌给上层后由 page.tsx 的 polling effect 接管，避免重复请求
      onJobChange(next);
    } catch (e: any) {
      setError(e?.message ?? "提交失败");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div className="text-[11.5px] uppercase tracking-[0.12em] text-tertiary">
          高光时刻 · {items.length}{" "}
          <span className="ml-1 normal-case tracking-normal text-secondary">
            （拖动调整顺序，垃圾桶移除）
          </span>
        </div>
        <div className="flex items-center gap-1">
          {dirty && (
            <button
              type="button"
              onClick={reset}
              disabled={busy}
              className="btn-ghost flex items-center gap-1 rounded-ios px-2 py-1 text-[11.5px]"
            >
              <RotateCcw className="h-3 w-3" />
              撤销
            </button>
          )}
          <motion.button
            whileTap={{ scale: 0.96 }}
            type="button"
            onClick={apply}
            disabled={!dirty || busy}
            className={`inline-flex items-center gap-1 rounded-ios px-3 py-1 text-[12px] font-semibold transition ${
              dirty && !busy
                ? "btn-ios"
                : "border border-line bg-black/[0.04] text-tertiary"
            }`}
          >
            <Check className={`h-3.5 w-3.5 ${busy ? "animate-spin" : ""}`} />
            {busy ? "重剪中…" : "按当前顺序重剪"}
          </motion.button>
        </div>
      </div>

      <Reorder.Group
        axis="y"
        values={items}
        onReorder={setItems}
        className="space-y-1.5"
      >
        <AnimatePresence initial={false}>
          {items.map((h, i) => (
            <Reorder.Item
              key={keyOf(h)}
              value={h}
              dragListener={!busy}
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.92 }}
              transition={{ type: "spring", stiffness: 380, damping: 26 }}
              className="group flex items-center gap-2 rounded-ios border border-line2 bg-black/[0.03] px-2.5 py-1.5 text-[13px] transition hover:border-accent/30 hover:bg-black/[0.05]"
            >
              <span className="grid h-5 w-5 cursor-grab place-items-center rounded-full text-tertiary active:cursor-grabbing">
                <GripVertical className="h-3.5 w-3.5" />
              </span>
              <span className="w-5 text-right tabular-nums text-tertiary">
                {i + 1}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-secondary tabular-nums">
                    {h.start.toFixed(1)}s – {h.end.toFixed(1)}s
                  </span>
                  <span className="text-[11px] text-tertiary">
                    · {(h.end - h.start).toFixed(1)}s
                  </span>
                </div>
                <div className="truncate text-[11.5px] text-tertiary">
                  {h.phrase || h.reason || "—"}
                </div>
              </div>
              <span className="shrink-0 rounded-full bg-black/8 px-2 py-0.5 text-[11px] tabular-nums text-secondary">
                {(h.score * 100).toFixed(0)}
              </span>
              <button
                type="button"
                onClick={() => remove(h)}
                disabled={busy}
                className="grid h-6 w-6 place-items-center rounded-full text-tertiary opacity-0 transition group-hover:opacity-100 hover:bg-pink/15 hover:text-pink"
                title="移除这段"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </Reorder.Item>
          ))}
        </AnimatePresence>
      </Reorder.Group>

      {items.length === 0 && (
        <div className="rounded-ios border border-dashed border-line2 px-3 py-4 text-center text-[12.5px] text-tertiary">
          全部移除了，至少保留一段
        </div>
      )}

      {error && (
        <div className="rounded-ios border border-pink/30 bg-pink/10 px-3 py-2 text-[12.5px] text-pink">
          {error}
        </div>
      )}
    </div>
  );
}
