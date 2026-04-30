"use client";
import { useEffect, useRef, useState } from "react";
import { Wand2, Sparkles, Github } from "lucide-react";
import { UploadZone } from "@/components/UploadZone";
import { KeywordPicker } from "@/components/KeywordPicker";
import { ProgressView } from "@/components/ProgressView";
import { ResultPanel } from "@/components/ResultPanel";
import { createJob, getJob, type Job } from "@/lib/api";

export default function HomePage() {
  const [files, setFiles] = useState<File[]>([]);
  const [keywords, setKeywords] = useState<string[]>([]);
  const [style, setStyle] = useState<string>("燃");
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
    <main className="mx-auto max-w-6xl px-5 py-10">
      <header className="mb-10 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-sm text-accent2">
            <Sparkles className="h-4 w-4" />
            <span>SportClip · 多合一运动视频剪辑</span>
          </div>
          <h1 className="mt-2 text-3xl font-bold tracking-tight md:text-4xl">
            一键识别 ·{" "}
            <span className="bg-gradient-to-r from-accent to-accent2 bg-clip-text text-transparent">
              高光剪辑
            </span>{" "}
            · 文案直出
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-white/60">
            上传你的运动素材，本地 YOLO + 云端 VLM 自动识别运动种类、检出高光时刻、剪辑成片，并按你选的关键字生成分享文案。
          </p>
        </div>
        <a
          href="https://github.com/ultralytics/ultralytics"
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-1.5 rounded-lg border border-line bg-white/[0.02] px-3 py-1.5 text-xs text-white/70 hover:border-accent/40"
        >
          <Github className="h-4 w-4" />
          基于 YOLOv8
        </a>
      </header>

      {!job && (
        <div className="grid gap-6 md:grid-cols-2">
          <section>
            <h2 className="mb-3 text-sm font-medium text-white/70">1. 上传视频</h2>
            <UploadZone files={files} onChange={setFiles} />
          </section>
          <section>
            <h2 className="mb-3 text-sm font-medium text-white/70">2. 文案关键字 + 风格</h2>
            <KeywordPicker
              keywords={keywords}
              onKeywords={setKeywords}
              style={style}
              onStyle={setStyle}
            />
          </section>
        </div>
      )}

      {!job && (
        <div className="mt-8 flex items-center justify-between">
          {error ? (
            <div className="text-sm text-red-400">{error}</div>
          ) : (
            <div className="text-xs text-white/40">
              {files.length} 个视频 · {keywords.length} 个关键词 · 风格: {style}
            </div>
          )}
          <button
            type="button"
            onClick={submit}
            disabled={submitting || !files.length}
            className="group inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-accent to-accent2 px-5 py-2.5 font-medium text-black shadow-lg shadow-accent/20 transition disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Wand2 className="h-4 w-4" />
            {submitting ? "正在上传…" : "开始剪辑"}
          </button>
        </div>
      )}

      {showProgress && job && (
        <div className="mt-2">
          <ProgressView job={job} />
          {job.stage === "failed" && (
            <button
              type="button"
              onClick={reset}
              className="mt-3 rounded-lg border border-line bg-white/[0.02] px-3 py-1.5 text-sm hover:border-accent/40"
            >
              返回重试
            </button>
          )}
        </div>
      )}

      {showResult && job && (
        <div className="mt-2 space-y-4">
          <ResultPanel job={job} />
          <div className="flex justify-end">
            <button
              type="button"
              onClick={reset}
              className="rounded-lg border border-line bg-white/[0.02] px-3 py-1.5 text-sm hover:border-accent/40"
            >
              再剪一支
            </button>
          </div>
        </div>
      )}

      <footer className="mt-16 border-t border-line/60 pt-6 text-xs text-white/40">
        本项目为原型 Demo · YOLOv8 + ffmpeg + LLM 协同 ·{" "}
        <span className="text-white/60">数据仅在本机处理</span>
      </footer>
    </main>
  );
}
