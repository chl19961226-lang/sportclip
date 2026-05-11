"use client";
import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";
import { Sparkles, Plus, X } from "lucide-react";

const SUGGESTIONS = [
  "今日训练", "城市夜跑", "投篮", "扣篮", "三分", "急停跳投",
  "雪场首滑", "powder day", "压雪刀", "single black",
  "顶绳攀登", "抱石", "v5+", "外岩",
  "晨间瑜伽", "马拉松", "PB", "突破自我", "热爱",
];

const STYLES: Array<{ key: string; desc: string; tone: string }> = [
  { key: "燃", desc: "热血冲击", tone: "bg-pink/15 text-pink border-pink/30" },
  { key: "治愈", desc: "温柔细腻", tone: "bg-teal/15 text-teal border-teal/30" },
  { key: "搞笑", desc: "网感十足", tone: "bg-orange/15 text-orange border-orange/30" },
  { key: "专业", desc: "技术向", tone: "bg-accent/15 text-accent border-accent/30" },
  { key: "vlog", desc: "生活感", tone: "bg-indigo/15 text-indigo border-indigo/30" },
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
    <div className="space-y-6">
      <div>
        <div className="mb-2.5 flex items-center gap-2 text-[13px] font-medium text-secondary">
          <Sparkles className="h-3.5 w-3.5 text-accent" />
          文案关键字
        </div>
        <div className="flex flex-wrap gap-2">
          <AnimatePresence initial={false}>
            {keywords.map((k) => (
              <motion.span
                key={k}
                layout
                initial={{ opacity: 0, scale: 0.85 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.85 }}
                transition={{ type: "spring", stiffness: 380, damping: 24 }}
                className="flex items-center gap-1.5 rounded-full border border-accent/30 bg-accent/12 px-3 py-1 text-[13px] font-medium text-accent"
              >
                {k}
                <button
                  type="button"
                  onClick={() => onKeywords(keywords.filter((x) => x !== k))}
                  className="opacity-60 hover:opacity-100"
                >
                  <X className="h-3 w-3" />
                </button>
              </motion.span>
            ))}
          </AnimatePresence>
          <div className="flex items-center gap-1 rounded-full border border-line2 bg-black/5 px-2.5 py-1">
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
              className="w-44 bg-transparent text-[13px] outline-none placeholder:text-tertiary"
            />
            <motion.button
              type="button"
              whileTap={{ scale: 0.9 }}
              onClick={() => {
                add(text);
                setText("");
              }}
              className="grid h-6 w-6 place-items-center rounded-full text-secondary hover:bg-black/10 hover:text-primary"
            >
              <Plus className="h-3.5 w-3.5" />
            </motion.button>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {SUGGESTIONS.filter((s) => !keywords.includes(s)).map((s) => (
            <motion.button
              key={s}
              type="button"
              whileTap={{ scale: 0.94 }}
              onClick={() => add(s)}
              className="rounded-full border border-line bg-black/[0.03] px-2.5 py-0.5 text-[12px] text-tertiary transition hover:border-accent/40 hover:text-primary"
            >
              {s}
            </motion.button>
          ))}
        </div>
      </div>

      <div>
        <div className="mb-2.5 text-[13px] font-medium text-secondary">文案风格</div>
        <div className="flex flex-wrap gap-2">
          {STYLES.map((s) => {
            const active = style === s.key;
            return (
              <motion.button
                key={s.key}
                type="button"
                whileTap={{ scale: 0.96 }}
                onClick={() => onStyle(s.key)}
                animate={{
                  borderColor: active ? "rgba(10,132,255,0.55)" : "rgba(255,255,255,0.10)",
                }}
                transition={{ type: "spring", stiffness: 360, damping: 26 }}
                className={`group relative rounded-ios border px-3.5 py-2.5 text-left transition ${
                  active
                    ? "bg-accent/12 shadow-glow"
                    : "bg-black/[0.03] hover:bg-black/[0.06]"
                }`}
              >
                <div className="text-[14px] font-semibold tracking-tight text-primary">
                  {s.key}
                </div>
                <div className="text-[11.5px] text-tertiary">{s.desc}</div>
                {active && (
                  <motion.div
                    layoutId="style-glow"
                    className="absolute inset-0 -z-10 rounded-ios bg-gradient-to-br from-accent/20 to-indigo/20 blur-xl"
                  />
                )}
              </motion.button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
