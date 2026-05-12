"use client";
import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { Wand2, Sparkles, Github, Camera, Clock, FolderOpen, Layers } from "lucide-react";
import { UploadZone } from "@/components/UploadZone";
import { KeywordPicker } from "@/components/KeywordPicker";
import { ProgressView } from "@/components/ProgressView";
import { ResultPanel } from "@/components/ResultPanel";
import { TweakPanel } from "@/components/TweakPanel";
import { HistoryList } from "@/components/HistoryList";
import { LibraryPanel } from "@/components/LibraryPanel";
import { createJob, getJob, type Job, type JobMode } from "@/lib/api";

type Tab = "work" | "history" | "library";

export default function HomePage() {
  const [tab, setTab] = useState<Tab>("work");
  const [files, setFiles] = useState<File[]>([]);
  const [keywords, setKeywords] = useState<string[]>([]);
  const [style, setStyle] = useState<string>("vlog");
  const [title, setTitle] = useState<string>("");
  const [coverDate, setCoverDate] = useState<string>("");
  // 模式不再让用户选：1 个视频 = 短高光，≥2 个视频 = 合集长片
  const mode: JobMode = files.length >= 2 ? "compilation" : "highlight";
  const [job, setJob] = useState<Job | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 统一的 polling effect：只要 job 处于 "还没完成" 状态，就每 1.5s 拉一次
  useEffect(() => {
    const stop = () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
    if (!job) {
      stop();
      return;
    }
    if (job.stage === "done" || job.stage === "failed") {
      stop();
      return;
    }
    if (pollRef.current) return;
    pollRef.current = setInterval(async () => {
      try {
        const j = await getJob(job.id);
        setJob(j);
      } catch (e) {
        console.warn("poll failed", e);
      }
    }, 1500);
    return stop;
  }, [job?.id, job?.stage]);

  const submit = async () => {
    if (!files.length) {
      setError("请至少选择一个视频文件");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const created = await createJob({
        files,
        keywords,
        style,
        mode,
        title: title.trim() || undefined,
        coverDate: coverDate.trim() || undefined,
      });
      setJob(created);
    } catch (e: any) {
      setError(e?.message ?? "提交失败");
    } finally {
      setSubmitting(false);
    }
  };

  const reset = () => {
    setJob(null);
    setFiles([]);
    setKeywords([]);
    setError(null);
    setTitle("");
    setCoverDate("");
  };

  // 从历史 / 视频库进入：把 job 灌过来，自动切到当前任务 tab
  const enterJob = (j: Job) => {
    setJob(j);
    setTab("work");
  };

  // 一旦拿到成片就常驻 result 区（重剪过程中也保留，TweakPanel 自己 spinner）
  const hasResult = !!(job && job.output_video);
  const showResult = !!(job && (hasResult || job.stage === "done"));
  const showProgress = !!(job && !hasResult && job.stage !== "done");

  return (
    <main className="mx-auto max-w-6xl px-5 py-10 md:py-14">
      {/* —— Hero —— */}
      <motion.header
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.2, 0.8, 0.2, 1] }}
        className="mb-12 flex flex-wrap items-end justify-between gap-6"
      >
        <div className="max-w-2xl">
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="mb-4 inline-flex items-center gap-1.5 text-[12.5px] uppercase tracking-[0.18em] text-tertiary"
          >
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-accent" />
            高光剪辑师 · for athletes
          </motion.div>
          <h1 className="flex items-baseline gap-3 font-display text-[64px] font-semibold leading-[1] tracking-[-0.035em] text-primary md:text-[88px]">
            <span className="bg-gradient-to-br from-primary to-primary/70 bg-clip-text text-transparent">
              Crux
            </span>
            <span className="text-[18px] font-medium tracking-tight text-tertiary md:text-[22px]">
              /krʌks/
            </span>
          </h1>
          <p className="mt-3 font-display text-[16.5px] font-medium tracking-tight text-primary/90 md:text-[18px]">
            The crux of every move.
            <span className="text-tertiary"> · 把决定性的那一下留下来</span>
          </p>
          <p className="mt-4 max-w-xl text-[14.5px] leading-relaxed text-secondary">
            上传你的运动素材，
            <span className="text-primary">YOLO + CLIP + LLM</span>
             协同识别运动种类、检出真正的高光瞬间、自动剪辑加转场，
            并按你给的关键词生成有画面感的小红书文案。
          </p>
        </div>
        <motion.a
          whileHover={{ y: -1 }}
          whileTap={{ scale: 0.96 }}
          href="https://github.com/chl19961226-lang/sportclip"
          target="_blank"
          rel="noreferrer"
          className="btn-ghost flex items-center gap-2 rounded-ios px-3.5 py-2 text-[12.5px]"
        >
          <Github className="h-4 w-4" />
          GitHub
        </motion.a>
      </motion.header>

      {/* —— 顶部 Tab —— */}
      <TabBar tab={tab} onTab={setTab} />

      {/* —— 主体 —— */}
      <AnimatePresence mode="wait">
        {tab === "history" && (
          <motion.section
            key="history"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ type: "spring", stiffness: 240, damping: 26 }}
            className="mt-2"
          >
            <HistoryList onPick={enterJob} />
          </motion.section>
        )}

        {tab === "library" && (
          <motion.section
            key="library"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ type: "spring", stiffness: 240, damping: 26 }}
            className="mt-2"
          >
            <LibraryPanel onCreated={enterJob} />
          </motion.section>
        )}

        {tab === "work" && !job && (
          <motion.section
            key="setup"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ type: "spring", stiffness: 220, damping: 26 }}
            className="space-y-6"
          >
            <div className="grid gap-6 md:grid-cols-2">
              <Card index={1} title="上传视频" icon={<Camera className="h-3.5 w-3.5 text-accent" />}>
                <UploadZone files={files} onChange={setFiles} />
                <p className="mt-3 text-[11.5px] leading-relaxed text-tertiary">
                  ✨ 上传 1 个视频输出 <span className="text-secondary">短高光</span>；
                  上传多个视频自动拼成<span className="text-secondary">合集长片</span>（带片头）。
                </p>
              </Card>
              <Card index={2} title="关键词 + 风格" icon={<Sparkles className="h-3.5 w-3.5 text-pink" />}>
                <KeywordPicker
                  keywords={keywords}
                  onKeywords={setKeywords}
                  style={style}
                  onStyle={setStyle}
                />
              </Card>
            </div>
            <CompilationMeta
              show={files.length >= 2}
              title={title}
              onTitle={setTitle}
              coverDate={coverDate}
              onCoverDate={setCoverDate}
            />
          </motion.section>
        )}

        {tab === "work" && showProgress && job && (
          <motion.section
            key="progress"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
          >
            <ProgressView job={job} />
            {job.stage === "failed" && (
              <button
                type="button"
                onClick={reset}
                className="btn-ghost mt-4 rounded-ios px-3.5 py-2 text-[13px]"
              >
                返回重试
              </button>
            )}
          </motion.section>
        )}

        {tab === "work" && showResult && job && (
          <motion.section
            key="result"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="space-y-5"
          >
            <ResultPanel job={job} onJobChange={setJob} />
            <TweakPanel job={job} onJobChange={setJob} />
            <div className="flex justify-end gap-2">
              <motion.button
                whileTap={{ scale: 0.97 }}
                type="button"
                onClick={() => setTab("history")}
                className="btn-ghost rounded-ios px-3.5 py-2 text-[13px]"
              >
                看历史
              </motion.button>
              <motion.button
                whileTap={{ scale: 0.97 }}
                type="button"
                onClick={reset}
                className="btn-ghost rounded-ios px-3.5 py-2 text-[13px]"
              >
                再剪一支
              </motion.button>
            </div>
          </motion.section>
        )}
      </AnimatePresence>

      {/* —— 提交栏（粘底 / 大型 iOS 主按钮） —— */}
      {tab === "work" && !job && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, type: "spring", stiffness: 220, damping: 26 }}
          className="mt-8 flex flex-wrap items-center justify-between gap-4 rounded-iosXl border border-line bg-black/[0.04] px-5 py-4 backdrop-blur-ios"
        >
          <div className="flex flex-wrap items-center gap-3 text-[13px] text-secondary">
            {error ? (
              <span className="text-pink">{error}</span>
            ) : (
              <>
                <span className="rounded-full bg-accent/12 px-2 py-0.5 text-[12px] font-medium text-accent">
                  {mode === "compilation" ? "合集长片" : "短高光"}
                </span>
                <span className="rounded-full bg-black/8 px-2 py-0.5 text-[12px]">
                  {files.length} 个视频
                </span>
                <span className="rounded-full bg-black/8 px-2 py-0.5 text-[12px]">
                  {keywords.length} 个关键词
                </span>
                <span className="rounded-full bg-black/8 px-2 py-0.5 text-[12px]">
                  风格 · {style}
                </span>
              </>
            )}
          </div>
          <motion.button
            whileTap={{ scale: 0.97 }}
            type="button"
            onClick={submit}
            disabled={submitting || !files.length}
            className="btn-ios inline-flex items-center gap-2 rounded-ios px-5 py-2.5 text-[15px] font-semibold tracking-tight"
          >
            <Wand2 className="h-4 w-4" />
            {submitting ? "正在上传…" : "开始剪辑"}
          </motion.button>
        </motion.div>
      )}

      <footer className="mt-20 flex flex-wrap items-center justify-between gap-3 border-t border-line/60 pt-6 text-[12px] text-tertiary">
        <div>
          <span className="font-display text-[13px] font-semibold tracking-tight text-secondary">
            Crux
          </span>
          <span> · YOLOv8 + CLIP + ffmpeg + LLM 协同</span>
        </div>
        <span className="text-secondary">数据仅在本机处理</span>
      </footer>
    </main>
  );
}

const TABS: Array<{ key: Tab; label: string; icon: React.ReactNode }> = [
  { key: "work", label: "当前任务", icon: <Wand2 className="h-3.5 w-3.5" /> },
  { key: "history", label: "历史记录", icon: <Clock className="h-3.5 w-3.5" /> },
  { key: "library", label: "视频库", icon: <FolderOpen className="h-3.5 w-3.5" /> },
];

function TabBar({ tab, onTab }: { tab: Tab; onTab: (t: Tab) => void }) {
  return (
    <div className="mb-6 inline-flex rounded-full border border-line2 bg-black/[0.04] p-0.5">
      {TABS.map((t) => {
        const active = tab === t.key;
        return (
          <button
            key={t.key}
            type="button"
            onClick={() => onTab(t.key)}
            className={`relative inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-[13px] font-medium transition ${
              active ? "text-white" : "text-secondary hover:text-primary"
            }`}
          >
            {active && (
              <motion.span
                layoutId="tab-pill"
                className="absolute inset-0 -z-10 rounded-full bg-primary shadow-glow"
                transition={{ type: "spring", stiffness: 380, damping: 30 }}
              />
            )}
            {t.icon}
            {t.label}
          </button>
        );
      })}
    </div>
  );
}

function Card({
  index,
  title,
  icon,
  children,
}: {
  index: number;
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <motion.section
      layout
      whileHover={{ y: -1 }}
      transition={{ type: "spring", stiffness: 320, damping: 28 }}
      className="glass rounded-iosXl p-5 md:p-6"
    >
      <div className="mb-4 flex items-center gap-2 text-[12.5px] text-secondary">
        <span className="grid h-5 w-5 place-items-center rounded-full bg-black/8 text-[10.5px] font-semibold text-primary">
          {index}
        </span>
        {icon}
        <span className="text-primary">{title}</span>
      </div>
      {children}
    </motion.section>
  );
}

/**
 * 合集元数据：仅当用户上传 ≥ 2 个视频时浮现。
 * 因为多视频会自动拼成合集长片，需要给个标题/日期当片头大字。
 */
function CompilationMeta({
  show,
  title,
  onTitle,
  coverDate,
  onCoverDate,
}: {
  show: boolean;
  title: string;
  onTitle: (s: string) => void;
  coverDate: string;
  onCoverDate: (s: string) => void;
}) {
  return (
    <AnimatePresence initial={false}>
      {show && (
        <motion.section
          key="meta"
          layout
          initial={{ opacity: 0, y: 8, height: 0 }}
          animate={{ opacity: 1, y: 0, height: "auto" }}
          exit={{ opacity: 0, y: -4, height: 0 }}
          transition={{ type: "spring", stiffness: 260, damping: 28 }}
          className="glass overflow-hidden rounded-iosXl p-5 md:p-6"
        >
          <div className="mb-4 flex items-center gap-2 text-[12.5px] text-secondary">
            <Layers className="h-3.5 w-3.5 text-indigo" />
            <span className="text-primary">合集片头（多视频自动拼合）</span>
            <span className="text-tertiary">· 可全部留空让系统自动生成</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
            <label className="flex flex-col gap-1.5">
              <span className="text-[12px] font-medium text-secondary">
                合集标题
              </span>
              <input
                value={title}
                onChange={(e) => onTitle(e.target.value)}
                placeholder="例：5.7 滑雪集锦"
                maxLength={22}
                className="rounded-ios border border-line2 bg-white/70 px-3 py-2 text-[14px] tracking-tight text-primary outline-none transition placeholder:text-tertiary focus:border-accent/60 focus:bg-white"
              />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-[12px] font-medium text-secondary">
                日期 / 副标题
              </span>
              <input
                value={coverDate}
                onChange={(e) => onCoverDate(e.target.value)}
                placeholder="例：May 7"
                maxLength={16}
                className="w-40 rounded-ios border border-line2 bg-white/70 px-3 py-2 text-[14px] tracking-tight text-primary outline-none transition placeholder:text-tertiary focus:border-accent/60 focus:bg-white"
              />
            </label>
          </div>
        </motion.section>
      )}
    </AnimatePresence>
  );
}
