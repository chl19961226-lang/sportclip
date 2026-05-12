"use client";
import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import { Sliders, RefreshCcw, Sparkles, Wand2 } from "lucide-react";
import {
  type Job,
  type JobMode,
  type RecutParams,
  recutJob,
  recaptionJob,
  getJob,
  SUPPORTED_SPORTS,
} from "@/lib/api";

type Props = {
  job: Job;
  onJobChange: (j: Job) => void;
};

const STYLES: Array<{ key: string; desc: string }> = [
  { key: "燃", desc: "热血冲击" },
  { key: "治愈", desc: "温柔细腻" },
  { key: "搞笑", desc: "网感十足" },
  { key: "专业", desc: "技术向" },
  { key: "vlog", desc: "生活感" },
];

export function TweakPanel({ job, onJobChange }: Props) {
  // 本地草稿——用户改动后再点"应用并重剪"
  const [mode, setMode] = useState<JobMode>(job.mode);
  const [sportType, setSportType] = useState<string>(job.sport_type ?? "");
  const [title, setTitle] = useState<string>(job.title ?? "");
  const [coverDate, setCoverDate] = useState<string>(job.cover_date ?? "");
  const [maxClips, setMaxClips] = useState<number>(job.max_clips);
  const [clipDuration, setClipDuration] = useState<number>(job.clip_duration_sec);
  const [minScore, setMinScore] = useState<number>(job.min_score ?? 0);
  const [perSourceMax, setPerSourceMax] = useState<number>(job.per_source_max);
  const [totalMax, setTotalMax] = useState<number>(job.total_max);
  const [minPerSource, setMinPerSource] = useState<number>(job.min_per_source);

  // 文案区
  const [style, setStyle] = useState<string>(job.style);
  const [keywordsText, setKeywordsText] = useState<string>(
    (job.keywords ?? []).join(", ")
  );

  const [recutting, setRecutting] = useState(false);
  const [recaptioning, setRecaptioning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 当 job 从外部刷新时，把"未编辑过的字段"同步过来；
  // 已编辑过的字段保持本地草稿，不被覆盖。
  // 简化处理：每次 job.id 变化时整体重置。
  useEffect(() => {
    setMode(job.mode);
    setSportType(job.sport_type ?? "");
    setTitle(job.title ?? "");
    setCoverDate(job.cover_date ?? "");
    setMaxClips(job.max_clips);
    setClipDuration(job.clip_duration_sec);
    setMinScore(job.min_score ?? 0);
    setPerSourceMax(job.per_source_max);
    setTotalMax(job.total_max);
    setMinPerSource(job.min_per_source);
    setStyle(job.style);
    setKeywordsText((job.keywords ?? []).join(", "));
    setError(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job.id]);

  const dirty = useMemo(() => {
    return (
      mode !== job.mode ||
      (sportType || "") !== (job.sport_type || "") ||
      (title || "") !== (job.title || "") ||
      (coverDate || "") !== (job.cover_date || "") ||
      maxClips !== job.max_clips ||
      Math.abs(clipDuration - job.clip_duration_sec) > 1e-3 ||
      Math.abs(minScore - (job.min_score ?? 0)) > 1e-3 ||
      perSourceMax !== job.per_source_max ||
      totalMax !== job.total_max ||
      minPerSource !== job.min_per_source
    );
  }, [
    mode, sportType, title, coverDate, maxClips, clipDuration, minScore,
    perSourceMax, totalMax, minPerSource, job,
  ]);

  const captionDirty =
    style !== job.style ||
    keywordsText.trim() !==
      (job.keywords ?? []).join(", ").trim() ||
    (sportType || "") !== (job.sport_type || "");

  const onRecut = async () => {
    setError(null);
    setRecutting(true);
    try {
      const params: RecutParams = {
        mode,
        sport_type: sportType || undefined,
        title: title || undefined,
        cover_date: coverDate || undefined,
        clip_duration_sec: clipDuration,
        min_score: minScore,
      };
      if (mode === "highlight") {
        params.max_clips = maxClips;
      } else {
        params.per_source_max = perSourceMax;
        params.total_max = totalMax;
        params.min_per_source = minPerSource;
      }
      let next = await recutJob(job.id, params);
      onJobChange(next);
      // 轮询直到完成
      while (next.stage !== "done" && next.stage !== "failed") {
        await new Promise((r) => setTimeout(r, 1500));
        next = await getJob(job.id);
        onJobChange(next);
      }
      if (next.stage === "failed") {
        setError(next.error ?? "重剪失败");
      }
    } catch (e: any) {
      setError(e?.message ?? "重剪失败");
    } finally {
      setRecutting(false);
    }
  };

  const onRecaption = async () => {
    setError(null);
    setRecaptioning(true);
    try {
      const kws = keywordsText
        .split(/[，,\s]+/)
        .map((s) => s.trim())
        .filter(Boolean);
      const next = await recaptionJob(job.id, {
        style,
        keywords: kws,
        sport_type: sportType || undefined,
      });
      onJobChange(next);
    } catch (e: any) {
      setError(e?.message ?? "文案生成失败");
    } finally {
      setRecaptioning(false);
    }
  };

  const isCompilation = mode === "compilation";
  const busy = recutting || recaptioning;

  return (
    <motion.section
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 220, damping: 26 }}
      className="glass space-y-6 rounded-iosXl p-5 md:p-6"
    >
      {/* ============= 头 ============= */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-[12.5px] text-secondary">
          <Sliders className="h-3.5 w-3.5 text-accent" />
          <span className="text-primary">微调与重新生成</span>
          <span className="text-tertiary">· 复用已分析的候选帧，无需再跑一次 YOLO/CLIP</span>
        </div>
      </div>

      {/* ============= 剪辑参数区 ============= */}
      <div className="space-y-5">
        {/* 模式 + 运动类型 */}
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="输出类型">
            <div className="inline-flex rounded-full border border-line2 bg-black/[0.04] p-0.5">
              {(["highlight", "compilation"] as JobMode[]).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setMode(m)}
                  className={`relative rounded-full px-3 py-1 text-[12.5px] font-medium transition ${
                    mode === m ? "text-white" : "text-secondary hover:text-primary"
                  }`}
                >
                  {mode === m && (
                    <motion.span
                      layoutId="tweak-mode-pill"
                      className="absolute inset-0 -z-10 rounded-full bg-accent shadow-glow"
                      transition={{ type: "spring", stiffness: 380, damping: 30 }}
                    />
                  )}
                  {m === "compilation" ? "合集长片" : "短高光"}
                </button>
              ))}
            </div>
          </Field>
          <Field label="运动类型纠正">
            <select
              value={sportType}
              onChange={(e) => setSportType(e.target.value)}
              className="w-full rounded-ios border border-line2 bg-white/70 px-3 py-2 text-[13.5px] text-primary outline-none transition focus:border-accent/60 focus:bg-white"
            >
              <option value="">{job.sport_type ?? "（自动识别）"}</option>
              {SUPPORTED_SPORTS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </Field>
        </div>

        {/* 合集才有的标题 / 日期 */}
        <AnimatePresence initial={false}>
          {isCompilation && (
            <motion.div
              key="compmeta"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ type: "spring", stiffness: 260, damping: 28 }}
              className="overflow-hidden"
            >
              <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
                <Field label="合集标题（片头大字）">
                  <input
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    maxLength={22}
                    placeholder="例：5.7 滑雪集锦"
                    className="rounded-ios border border-line2 bg-white/70 px-3 py-2 text-[14px] text-primary outline-none transition placeholder:text-tertiary focus:border-accent/60 focus:bg-white"
                  />
                </Field>
                <Field label="日期 / 副标题">
                  <input
                    value={coverDate}
                    onChange={(e) => setCoverDate(e.target.value)}
                    maxLength={16}
                    placeholder="例：May 7"
                    className="w-40 rounded-ios border border-line2 bg-white/70 px-3 py-2 text-[14px] text-primary outline-none transition placeholder:text-tertiary focus:border-accent/60 focus:bg-white"
                  />
                </Field>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* 数值参数（滑杆） */}
        <div className="grid gap-4 sm:grid-cols-2">
          {!isCompilation && (
            <Slider
              label="片段数量"
              value={maxClips}
              min={1}
              max={16}
              step={1}
              onChange={setMaxClips}
              format={(v) => `${v} 段`}
            />
          )}
          <Slider
            label="单段时长"
            value={clipDuration}
            min={isCompilation ? 3 : 1.5}
            max={isCompilation ? 12 : 6}
            step={0.5}
            onChange={setClipDuration}
            format={(v) => `${v.toFixed(1)} s`}
          />
          <Slider
            label="最低高光分阈值"
            hint="高于此分的帧才会入选；过严时系统会自动放宽以避免空成片"
            value={minScore}
            min={0}
            max={0.9}
            step={0.05}
            onChange={setMinScore}
            format={(v) => v.toFixed(2)}
          />
          {isCompilation && (
            <>
              <Slider
                label="每条源最多片段"
                value={perSourceMax}
                min={1}
                max={8}
                step={1}
                onChange={setPerSourceMax}
                format={(v) => `${v} 段`}
              />
              <Slider
                label="总段数上限"
                value={totalMax}
                min={4}
                max={36}
                step={1}
                onChange={setTotalMax}
                format={(v) => `${v} 段`}
              />
              <Slider
                label="每条源至少入选"
                hint="0 = 允许某条源全被丢；推荐 1 让每个素材都露脸"
                value={minPerSource}
                min={0}
                max={3}
                step={1}
                onChange={setMinPerSource}
                format={(v) => `${v} 段`}
              />
            </>
          )}
        </div>

        <div className="flex items-center justify-between gap-3">
          <span className="text-[12px] text-tertiary">
            {dirty ? "参数有改动，点右侧按钮应用并重剪" : "参数与当前一致"}
          </span>
          <motion.button
            whileTap={{ scale: 0.97 }}
            type="button"
            onClick={onRecut}
            disabled={busy}
            className="btn-ios inline-flex items-center gap-2 rounded-ios px-4 py-2 text-[14px] font-semibold disabled:cursor-not-allowed disabled:opacity-60"
          >
            <RefreshCcw className={`h-4 w-4 ${recutting ? "animate-spin" : ""}`} />
            {recutting ? "重剪中…" : "应用并重新剪辑"}
          </motion.button>
        </div>
      </div>

      <hr className="border-line/60" />

      {/* ============= 文案重新生成 ============= */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-[12.5px] text-secondary">
          <Sparkles className="h-3.5 w-3.5 text-pink" />
          <span className="text-primary">重新生成文案</span>
          <span className="text-tertiary">· 不重剪视频，只换风格 / 关键词</span>
        </div>

        <Field label="文案风格">
          <div className="flex flex-wrap gap-1.5">
            {STYLES.map((s) => {
              const active = style === s.key;
              return (
                <motion.button
                  key={s.key}
                  type="button"
                  whileTap={{ scale: 0.96 }}
                  onClick={() => setStyle(s.key)}
                  className={`rounded-full border px-3 py-1 text-[12.5px] font-medium transition ${
                    active
                      ? "border-accent/55 bg-accent/12 text-accent"
                      : "border-line2 bg-black/[0.03] text-secondary hover:text-primary"
                  }`}
                >
                  <span>{s.key}</span>
                  <span className="ml-1 text-[11px] text-tertiary">{s.desc}</span>
                </motion.button>
              );
            })}
          </div>
        </Field>

        <Field label="关键词（用空格 / 逗号分隔）">
          <input
            value={keywordsText}
            onChange={(e) => setKeywordsText(e.target.value)}
            placeholder="例：滑雪 立刃 雪粉"
            className="w-full rounded-ios border border-line2 bg-white/70 px-3 py-2 text-[14px] text-primary outline-none transition placeholder:text-tertiary focus:border-accent/60 focus:bg-white"
          />
        </Field>

        <div className="flex items-center justify-between gap-3">
          <span className="text-[12px] text-tertiary">
            {captionDirty ? "改了风格 / 关键词，点右侧重新生成" : "和当前文案参数一致"}
          </span>
          <motion.button
            whileTap={{ scale: 0.97 }}
            type="button"
            onClick={onRecaption}
            disabled={busy}
            className="btn-ghost inline-flex items-center gap-2 rounded-ios px-3.5 py-2 text-[13.5px] font-medium disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Wand2 className={`h-4 w-4 ${recaptioning ? "animate-spin" : ""}`} />
            {recaptioning ? "生成中…" : "再来一份文案"}
          </motion.button>
        </div>
      </div>

      {error && (
        <div className="rounded-ios border border-pink/30 bg-pink/10 px-3 py-2 text-[12.5px] text-pink">
          {error}
        </div>
      )}
    </motion.section>
  );
}

// ------------ 子组件 ------------ //
function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-[12px] font-medium text-secondary">{label}</span>
      {children}
    </label>
  );
}

function Slider({
  label,
  hint,
  value,
  min,
  max,
  step,
  onChange,
  format,
}: {
  label: string;
  hint?: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
  format: (v: number) => string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-[12px] font-medium text-secondary">
        <span>{label}</span>
        <span className="rounded-full bg-black/[0.06] px-2 py-0.5 text-[11.5px] tabular-nums text-primary">
          {format(value)}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-black/10 accent-accent"
      />
      {hint && <span className="text-[11px] leading-snug text-tertiary">{hint}</span>}
    </div>
  );
}
