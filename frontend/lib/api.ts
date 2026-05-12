// 后端 API 客户端。

export const API_BASE =
  (typeof window !== "undefined" && (window as any).__API_BASE__) ||
  process.env.NEXT_PUBLIC_API_BASE ||
  "http://localhost:8000";

export type Caption = {
  title: string;
  body: string;
  hashtags: string[];
};

export type Highlight = {
  src: string;
  start: number;
  end: number;
  score: number;
  reason: string;
  phrase?: string;
  image_path?: string;
};

export type JobMode = "highlight" | "compilation";

export type Job = {
  id: string;
  stage: string;
  stage_label: string;
  progress: number;
  message: string;
  error: string | null;
  keywords: string[];
  style: string;
  mode: JobMode;
  title: string | null;
  cover_date: string | null;
  // 可调剪辑参数
  max_clips: number;
  clip_duration_sec: number;
  min_score: number;
  per_source_max: number;
  total_max: number;
  min_per_source: number;
  // 识别 + 结果
  sport_type: string | null;
  sport_confidence: number;
  highlights: Highlight[];
  output_video: string | null;
  thumbnail: string | null;
  caption: Caption | null;
  created_at: number;
};

export async function createJob(input: {
  files: File[];
  keywords: string[];
  style: string;
  mode?: JobMode;
  title?: string;
  coverDate?: string;
}): Promise<Job> {
  const fd = new FormData();
  for (const f of input.files) fd.append("files", f);
  for (const kw of input.keywords) fd.append("keywords", kw);
  fd.append("style", input.style);
  if (input.mode) fd.append("mode", input.mode);
  if (input.title) fd.append("title", input.title);
  if (input.coverDate) fd.append("cover_date", input.coverDate);
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/jobs`, { method: "POST", body: fd });
  } catch (e: any) {
    // 典型原因：后端未启动 / 跨源被拦截 / 代理断连
    throw new Error(
      `无法连接后端（${API_BASE}）。请确认后端已启动，且 CORS 放行了当前页面来源。底层错误：${e?.message ?? e}`
    );
  }
  if (!res.ok) throw new Error(`upload failed: ${res.status} ${await res.text()}`);
  return res.json();
}

export async function getJob(id: string): Promise<Job> {
  const res = await fetch(`${API_BASE}/api/jobs/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`get job failed: ${res.status}`);
  return res.json();
}

export const fileUrl = (id: string, kind: "highlight" | "thumbnail") =>
  `${API_BASE}/api/files/${id}/${kind}`;

// ------------------------------------------------------------------ //
// 重新剪辑：复用已打分的候选帧，按新参数挑片 + 重剪。异步：返回 job
// 后请客户端继续 poll /api/jobs/:id 直到 stage === "done"。
// ------------------------------------------------------------------ //
export type RecutParams = {
  mode?: JobMode;
  sport_type?: string;
  title?: string;
  cover_date?: string;
  max_clips?: number;
  clip_duration_sec?: number;
  min_score?: number;
  per_source_max?: number;
  total_max?: number;
  min_per_source?: number;
};

export async function recutJob(id: string, params: RecutParams): Promise<Job> {
  const fd = new FormData();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null) continue;
    fd.append(k, String(v));
  }
  const res = await fetch(`${API_BASE}/api/jobs/${id}/recut`, {
    method: "POST",
    body: fd,
  });
  if (!res.ok) throw new Error(`recut failed: ${res.status} ${await res.text()}`);
  return res.json();
}

// ------------------------------------------------------------------ //
// 重新生成文案：仅基于现有 highlights 再调一次 LLM。同步等待。
// ------------------------------------------------------------------ //
export type RecaptionParams = {
  style?: string;
  keywords?: string[];
  sport_type?: string;
};

export async function recaptionJob(id: string, params: RecaptionParams): Promise<Job> {
  const fd = new FormData();
  if (params.style) fd.append("style", params.style);
  if (params.sport_type) fd.append("sport_type", params.sport_type);
  for (const kw of params.keywords ?? []) fd.append("keywords", kw);
  const res = await fetch(`${API_BASE}/api/jobs/${id}/recaption`, {
    method: "POST",
    body: fd,
  });
  if (!res.ok) throw new Error(`recaption failed: ${res.status} ${await res.text()}`);
  return res.json();
}

// 后端支持的运动种类（用于结果页"纠正运动类型"下拉）
export const SUPPORTED_SPORTS: string[] = [
  "双板滑雪", "单板滑雪", "攀岩", "抱石", "篮球", "足球", "网球",
  "跑步", "马拉松", "骑行", "冲浪", "滑板", "瑜伽", "拳击",
];

// ------------------------------------------------------------------ //
// 历史 / 视频库 / 拖拽排序
// ------------------------------------------------------------------ //
export async function listJobs(): Promise<Job[]> {
  const res = await fetch(`${API_BASE}/api/jobs`, { cache: "no-store" });
  if (!res.ok) throw new Error(`list jobs failed: ${res.status}`);
  const data = await res.json();
  return data.jobs ?? [];
}

export async function deleteJob(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/jobs/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`delete failed: ${res.status} ${await res.text()}`);
}

export type ReorderItem = { src: string; start: number; end: number };

export async function reorderJob(id: string, order: ReorderItem[]): Promise<Job> {
  const res = await fetch(`${API_BASE}/api/jobs/${id}/reorder`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ order }),
  });
  if (!res.ok) throw new Error(`reorder failed: ${res.status} ${await res.text()}`);
  return res.json();
}

export type LibraryItem = {
  src_id: string;
  job_id: string;
  index: number;
  file_name: string;
  thumbnail_url: string | null;
  sport_type: string | null;
  created_at: number;
  mode: JobMode;
  from_job_title: string | null;
};

export async function getLibrary(): Promise<LibraryItem[]> {
  const res = await fetch(`${API_BASE}/api/library`, { cache: "no-store" });
  if (!res.ok) throw new Error(`get library failed: ${res.status}`);
  const data = await res.json();
  return data.items ?? [];
}

export type FromLibraryParams = {
  src_ids: string[];
  mode?: JobMode;
  title?: string;
  cover_date?: string;
  style?: string;
  keywords?: string[];
};

export async function createJobFromLibrary(params: FromLibraryParams): Promise<Job> {
  const res = await fetch(`${API_BASE}/api/jobs/from_library`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(`from_library failed: ${res.status} ${await res.text()}`);
  return res.json();
}
