"use client";
import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useMemo, useState, useCallback } from "react";
import { RefreshCcw, Film, Layers, Wand2, X } from "lucide-react";
import {
  type Job,
  type LibraryItem,
  type JobMode,
  getLibrary,
  createJobFromLibrary,
} from "@/lib/api";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type Props = {
  onCreated: (job: Job) => void;
};

export function LibraryPanel({ onCreated }: Props) {
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string[]>([]); // src_id 顺序就是合成顺序
  const [title, setTitle] = useState("");
  const [coverDate, setCoverDate] = useState("");
  const [style, setStyle] = useState("vlog");
  const [submitting, setSubmitting] = useState(false);
  // 模式自动推断：选 1 条 → 短高光；≥2 条 → 合集
  const mode: JobMode = selected.length >= 2 ? "compilation" : "highlight";

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await getLibrary();
      setItems(list);
    } catch (e: any) {
      setError(e?.message ?? "加载视频库失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const toggle = (sid: string) => {
    setSelected((prev) =>
      prev.includes(sid) ? prev.filter((x) => x !== sid) : [...prev, sid]
    );
  };

  // 按运动类型 → 月份 双层分组
  const groups = useMemo(() => {
    type Bucket = { sport: string; months: Map<string, LibraryItem[]> };
    const byS: Map<string, Bucket> = new Map();
    for (const it of items) {
      const sport = it.sport_type ?? "未识别";
      let bucket = byS.get(sport);
      if (!bucket) {
        bucket = { sport, months: new Map() };
        byS.set(sport, bucket);
      }
      const m = monthKey(it.created_at);
      let arr = bucket.months.get(m);
      if (!arr) {
        arr = [];
        bucket.months.set(m, arr);
      }
      arr.push(it);
    }
    // 排序：sport 按 items 数量倒序；month 按时间倒序；item 按 created_at 倒序
    const sportList = Array.from(byS.values()).sort(
      (a, b) =>
        Array.from(b.months.values()).flat().length -
        Array.from(a.months.values()).flat().length
    );
    return sportList.map((b) => ({
      sport: b.sport,
      months: Array.from(b.months.entries())
        .map(([m, arr]) => ({ month: m, items: arr.sort((a, x) => x.created_at - a.created_at) }))
        .sort((a, x) => (x.month > a.month ? 1 : -1)),
    }));
  }, [items]);

  const submit = async () => {
    if (!selected.length) return;
    setError(null);
    setSubmitting(true);
    try {
      const job = await createJobFromLibrary({
        src_ids: selected,
        mode,
        title: title.trim() || undefined,
        cover_date: coverDate.trim() || undefined,
        style,
      });
      onCreated(job);
    } catch (e: any) {
      setError(e?.message ?? "提交失败");
    } finally {
      setSubmitting(false);
    }
  };

  const selectedSet = new Set(selected);
  const selectedItems = selected
    .map((sid) => items.find((i) => i.src_id === sid))
    .filter((x): x is LibraryItem => !!x);

  return (
    <div className="space-y-6 pb-32">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-[12.5px] text-secondary">
          <Layers className="h-3.5 w-3.5 text-indigo" />
          <span className="text-primary">已上传视频库</span>
          <span className="text-tertiary">
            · 共 {items.length} 条 · 多选后合成新合集
          </span>
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

      {!loading && items.length === 0 && (
        <div className="glass rounded-iosXl px-5 py-12 text-center text-[13px] text-tertiary">
          视频库还是空的。先去「当前任务」上传素材生成一次后回来看看 🎬
        </div>
      )}

      {/* —— 按 运动 + 月份 分组 —— */}
      {groups.map((g) => (
        <section key={g.sport} className="space-y-3">
          <div className="flex items-center gap-2 text-[13px]">
            <span className="rounded-full bg-accent/15 px-3 py-0.5 text-[12px] font-medium text-accent">
              {g.sport}
            </span>
            <span className="text-tertiary">
              · {g.months.reduce((s, m) => s + m.items.length, 0)} 条
            </span>
          </div>
          {g.months.map((m) => (
            <div key={`${g.sport}-${m.month}`} className="space-y-2">
              <div className="text-[11.5px] uppercase tracking-[0.12em] text-tertiary">
                {m.month}
              </div>
              <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-4">
                {m.items.map((it) => {
                  const checked = selectedSet.has(it.src_id);
                  const order = checked ? selected.indexOf(it.src_id) + 1 : 0;
                  return (
                    <motion.button
                      key={it.src_id}
                      layout
                      type="button"
                      whileTap={{ scale: 0.98 }}
                      onClick={() => toggle(it.src_id)}
                      className={`glass relative overflow-hidden rounded-iosXl text-left transition ${
                        checked ? "ring-2 ring-accent/70" : ""
                      }`}
                    >
                      <div className="relative aspect-video w-full bg-black/[0.06]">
                        {it.thumbnail_url ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={`${API_BASE}${it.thumbnail_url}`}
                            alt={it.file_name}
                            className="h-full w-full object-cover"
                          />
                        ) : (
                          <div className="grid h-full place-items-center text-tertiary">
                            <Film className="h-6 w-6 opacity-40" />
                          </div>
                        )}
                        <div
                          className={`absolute right-2 top-2 grid h-7 w-7 place-items-center rounded-full text-[12px] font-semibold transition ${
                            checked
                              ? "bg-accent text-white shadow-glow"
                              : "bg-black/55 text-white opacity-0 group-hover:opacity-100"
                          }`}
                        >
                          {checked ? order : ""}
                        </div>
                      </div>
                      <div className="space-y-0.5 p-3">
                        <div className="truncate text-[13px] font-medium tracking-tight text-primary">
                          {it.file_name}
                        </div>
                        <div className="text-[11px] text-tertiary">
                          {formatDate(it.created_at)}
                        </div>
                      </div>
                    </motion.button>
                  );
                })}
              </div>
            </div>
          ))}
        </section>
      ))}

      {/* —— 底栏：选中后浮现 —— */}
      <AnimatePresence>
        {selected.length > 0 && (
          <motion.div
            key="bar"
            initial={{ y: 80, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 80, opacity: 0 }}
            transition={{ type: "spring", stiffness: 240, damping: 26 }}
            className="fixed inset-x-0 bottom-4 z-30 mx-auto max-w-5xl px-5"
          >
            <div className="glass rounded-iosXl border border-line bg-black/[0.04] p-4 shadow-xl backdrop-blur-ios">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-2 text-[12.5px] text-secondary">
                  <span className="rounded-full bg-accent/15 px-2.5 py-0.5 text-[12px] font-medium text-accent">
                    已选 {selected.length}
                  </span>
                  <span className="truncate text-tertiary">
                    顺序：{selectedItems.map((x) => x.file_name).join(" → ")}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setSelected([])}
                    className="btn-ghost flex items-center gap-1 rounded-ios px-3 py-1.5 text-[12.5px]"
                  >
                    <X className="h-3.5 w-3.5" />
                    清空
                  </button>
                </div>
              </div>

              <div className="mt-3 grid gap-2 sm:grid-cols-[1fr_auto_auto]">
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="合集标题（可空）"
                  maxLength={22}
                  className="rounded-ios border border-line2 bg-white/70 px-3 py-2 text-[13.5px] text-primary outline-none transition placeholder:text-tertiary focus:border-accent/60 focus:bg-white"
                />
                <input
                  value={coverDate}
                  onChange={(e) => setCoverDate(e.target.value)}
                  placeholder="日期"
                  maxLength={16}
                  className="w-32 rounded-ios border border-line2 bg-white/70 px-3 py-2 text-[13.5px] text-primary outline-none transition placeholder:text-tertiary focus:border-accent/60 focus:bg-white"
                />
                <select
                  value={style}
                  onChange={(e) => setStyle(e.target.value)}
                  className="rounded-ios border border-line2 bg-white/70 px-2 py-2 text-[13.5px] text-primary outline-none focus:border-accent/60 focus:bg-white"
                >
                  {["燃", "治愈", "搞笑", "专业", "vlog"].map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>

              <div className="mt-3 flex justify-end">
                <motion.button
                  whileTap={{ scale: 0.97 }}
                  type="button"
                  onClick={submit}
                  disabled={submitting}
                  className="btn-ios inline-flex items-center gap-2 rounded-ios px-4 py-2 text-[14px] font-semibold disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {submitting ? (
                    <>
                      <RefreshCcw className="h-4 w-4 animate-spin" />
                      创建中…
                    </>
                  ) : (
                    <>
                      <Wand2 className="h-4 w-4" />
                      合成 {selected.length} 段为新{mode === "compilation" ? "合集" : "高光"}
                    </>
                  )}
                </motion.button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function monthKey(ts: number): string {
  const d = new Date(ts * 1000);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function formatDate(ts: number): string {
  const d = new Date(ts * 1000);
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}
