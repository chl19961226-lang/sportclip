"use client";
import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { Wand2, Sparkles, Github, Camera } from "lucide-react";
import { UploadZone } from "@/components/UploadZone";
import { KeywordPicker } from "@/components/KeywordPicker";
import { ProgressView } from "@/components/ProgressView";
import { ResultPanel } from "@/components/ResultPanel";
import { createJob, getJob, type Job } from "@/lib/api";

export default function HomePage() {
  const [files, setFiles] = useState<File[]>([]);
  const [keywords, setKeywords] = useState<string[]>([]);
  const [style, setStyle] = useState<string>("vlog");
  const [job, setJob] = useState<Job | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const submit = async () => {
    if (!files.length) {
      setError("请至少选择一个视频文件");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const created = await createJob({ files, keywords, style });
      setJob(created);
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(async () => {
        try {
          const j = await getJob(created.id);
          setJob(j);
          if (j.stage === "done" || j.stage === "failed") {
            if (pollRef.current) {
              clearInterval(pollRef.current);
              pollRef.current = null;
            }
          }
        } catch (e) {
          console.warn("poll failed", e);
        }
      }, 1500);
    } catch (e: any) {
      setError(e?.message ?? "提交失败");
    } finally {
      setSubmitting(false);
    }
  };

  const reset = () => {
    if (pollRef.current) clearInterval(pollRef.current);
    setJob(null);
    setFiles([]);
    setKeywords([]);
    setError(null);
  };

  const showResult = job && job.stage === "done";
  const showProgress = job && job.stage !== "done";

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

      {/* —— 主体 —— */}
      <AnimatePresence mode="wait">
        {!job && (
          <motion.section
            key="setup"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ type: "spring", stiffness: 220, damping: 26 }}
            className="grid gap-6 md:grid-cols-2"
          >
            <Card index={1} title="上传视频" icon={<Camera className="h-3.5 w-3.5 text-accent" />}>
              <UploadZone files={files} onChange={setFiles} />
            </Card>
            <Card index={2} title="关键词 + 风格" icon={<Sparkles className="h-3.5 w-3.5 text-pink" />}>
              <KeywordPicker
                keywords={keywords}
                onKeywords={setKeywords}
                style={style}
                onStyle={setStyle}
              />
            </Card>
          </motion.section>
        )}

        {showProgress && job && (
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

        {showResult && job && (
          <motion.section
            key="result"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="space-y-5"
          >
            <ResultPanel job={job} />
            <div className="flex justify-end">
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
      {!job && (
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
