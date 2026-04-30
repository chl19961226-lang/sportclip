"use client";
import { useState } from "react";
import { Sparkles, Plus, X } from "lucide-react";

const SUGGESTIONS = [
  "今日训练", "城市夜跑", "投篮", "扣篮", "三分", "急停跳投",
  "雪场首滑", "powder day", "压雪刀", "single black",
  "顶绳攀登", "抱石", "v5+", "抱石难关",
  "晨间瑜伽", "马拉松", "PB", "突破自我", "打卡", "热爱",
];

const STYLES = [
  { key: "燃", desc: "热血冲击" },
  { key: "治愈", desc: "温柔细腻" },
  { key: "搞笑", desc: "网感十足" },
  { key: "专业", desc: "技术向" },
  { key: "vlog", desc: "生活感" },
];

type Props = {
  keywords: string[];
  onKeywords: (kw: string[]) => void;
  style: string;
  onStyle: (s: string) => void;
};

export function KeywordPicker({ keywords, onKeywords, style, onStyle }: Props) {
  const [text, setText] = useState("");
  const add = (k: string) => {
    const v = k.trim();
    if (!v || keywords.includes(v)) return;
    onKeywords([...keywords, v]);
  };
  return (
    <div className="space-y-5">
      <div>
        <div className="mb-2 flex items-center gap-2 text-sm text-white/70">
          <Sparkles className="h-4 w-4 text-accent2" />
          文案关键字
        </div>
        <div className="flex flex-wrap gap-2">
          {keywords.map((k) => (
            <span
              key={k}
              className="group flex items-center gap-1 rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-sm"
            >
              {k}
              <button
                type="button"
                onClick={() => onKeywords(keywords.filter((x) => x !== k))}
                className="text-white/50 hover:text-white"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
          <div className="flex items-center gap-1 rounded-full border border-line bg-panel/60 px-2 py-1">
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  add(text);
                  setText("");
                }
              }}
              placeholder="自定义关键词，回车确认"
              className="w-44 bg-transparent px-1 text-sm outline-none placeholder:text-white/30"
            />
            <button
              type="button"
              onClick={() => {
                add(text);
                setText("");
              }}
              className="rounded-full p-1 text-white/60 hover:bg-white/5 hover:text-white"
            >
              <Plus className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {SUGGESTIONS.filter((s) => !keywords.includes(s)).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => add(s)}
              className="rounded-full border border-line/80 bg-white/[0.02] px-2.5 py-0.5 text-xs text-white/60 hover:border-accent/40 hover:text-white"
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <div>
        <div className="mb-2 text-sm text-white/70">文案风格</div>
        <div className="flex flex-wrap gap-2">
          {STYLES.map((s) => (
            <button
              key={s.key}
              type="button"
              onClick={() => onStyle(s.key)}
              className={`rounded-xl border px-3 py-2 text-left transition ${
                style === s.key
                  ? "border-accent bg-accent/15 text-white"
                  : "border-line bg-white/[0.02] text-white/70 hover:border-accent/40"
              }`}
            >
              <div className="text-sm font-medium">{s.key}</div>
              <div className="text-[11px] text-white/50">{s.desc}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
