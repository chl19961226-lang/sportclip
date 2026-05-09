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

export type Job = {
  id: string;
  stage: string;
  stage_label: string;
  progress: number;
  message: string;
  error: string | null;
  keywords: string[];
  style: string;
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
}): Promise<Job> {
  const fd = new FormData();
  for (const f of input.files) fd.append("files", f);
  for (const kw of input.keywords) fd.append("keywords", kw);
  fd.append("style", input.style);
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
