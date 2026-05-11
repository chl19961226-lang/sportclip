"use client";
import { motion, AnimatePresence } from "framer-motion";
import { useCallback, useRef, useState } from "react";
import { UploadCloud, X, Film } from "lucide-react";

type Props = {
  files: File[];
  onChange: (files: File[]) => void;
};

function fmt(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

export function UploadZone({ files, onChange }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);

  const merge = useCallback(
    (incoming: FileList | File[]) => {
      const arr = Array.from(incoming).filter((f) => f.type.startsWith("video/"));
      if (!arr.length) return;
      const map = new Map<string, File>();
      for (const f of [...files, ...arr]) map.set(`${f.name}-${f.size}`, f);
      onChange(Array.from(map.values()));
    },
    [files, onChange]
  );

  return (
    <div className="space-y-4">
      <motion.label
        htmlFor="upload-input"
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          if (e.dataTransfer.files) merge(e.dataTransfer.files);
        }}
        animate={{
          scale: drag ? 1.01 : 1,
          borderColor: drag ? "rgba(10,132,255,0.55)" : "rgba(255,255,255,0.10)",
        }}
        transition={{ type: "spring", stiffness: 300, damping: 26 }}
        className="glass relative flex cursor-pointer flex-col items-center justify-center gap-3 rounded-iosXl border px-6 py-12 text-center transition"
      >
        <motion.div
          animate={{ y: drag ? -3 : 0 }}
          className="flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-accent/30 to-indigo/30 shadow-glow"
        >
          <UploadCloud className="h-7 w-7 text-accent" strokeWidth={2.2} />
        </motion.div>
        <div className="font-display text-[17px] font-semibold tracking-tight text-primary">
          拖入视频，或<span className="text-accent"> 点击选择</span>
        </div>
        <div className="text-[13px] text-secondary">
          支持 MP4 / MOV · 单条建议 ≤ 2 分钟 · 可多选
        </div>
        <input
          id="upload-input"
          ref={inputRef}
          type="file"
          accept="video/*"
          multiple
          className="hidden"
          onChange={(e) => e.target.files && merge(e.target.files)}
        />
      </motion.label>

      <AnimatePresence initial={false}>
        {files.length > 0 && (
          <motion.ul
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="space-y-2 overflow-hidden"
          >
            {files.map((f, i) => (
              <motion.li
                key={`${f.name}-${f.size}-${i}`}
                layout
                initial={{ opacity: 0, y: 8, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, x: 12, scale: 0.96 }}
                transition={{ type: "spring", stiffness: 320, damping: 28 }}
                className="glass flex items-center justify-between gap-3 rounded-ios px-3.5 py-2.5"
              >
                <div className="flex min-w-0 items-center gap-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px] bg-black/5">
                    <Film className="h-4 w-4 text-secondary" />
                  </div>
                  <div className="min-w-0">
                    <div className="truncate text-[14px] font-medium text-primary">
                      {f.name}
                    </div>
                    <div className="text-[11.5px] text-tertiary">{fmt(f.size)}</div>
                  </div>
                </div>
                <motion.button
                  type="button"
                  whileTap={{ scale: 0.92 }}
                  onClick={() => onChange(files.filter((_, j) => j !== i))}
                  className="grid h-8 w-8 place-items-center rounded-full text-tertiary hover:bg-black/8 hover:text-primary"
                  aria-label="移除"
                >
                  <X className="h-4 w-4" />
                </motion.button>
              </motion.li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  );
}
