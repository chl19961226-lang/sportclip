"use client";
import { Upload, X, Film } from "lucide-react";
import { useCallback, useRef, useState } from "react";

type Props = {
  files: File[];
  onChange: (files: File[]) => void;
};

export function UploadZone({ files, onChange }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);

  const add = useCallback(
    (incoming: FileList | File[]) => {
      const arr = Array.from(incoming).filter((f) => f.type.startsWith("video/"));
      onChange([...files, ...arr]);
    },
    [files, onChange]
  );

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          if (e.dataTransfer.files?.length) add(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        className={`glass cursor-pointer rounded-2xl border-dashed border-2 p-8 text-center transition
          ${drag ? "border-accent bg-accent/5" : "border-line hover:border-accent/60"}`}
      >
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-accent/15">
          <Upload className="h-6 w-6 text-accent" />
        </div>
        <div className="text-base font-medium">拖拽视频到这里 · 或点击选择文件</div>
        <div className="mt-1 text-sm text-white/50">
          支持多文件 · MP4 / MOV / AVI · 单文件建议 ≤ 500MB
        </div>
        <input
          ref={inputRef}
          type="file"
          accept="video/*"
          multiple
          hidden
          onChange={(e) => e.target.files && add(e.target.files)}
        />
      </div>

      {files.length > 0 && (
        <ul className="mt-4 space-y-2">
          {files.map((f, i) => (
            <li
              key={`${f.name}-${i}`}
              className="glass flex items-center justify-between rounded-xl px-3 py-2"
            >
              <div className="flex min-w-0 items-center gap-3">
                <Film className="h-4 w-4 shrink-0 text-accent2" />
                <span className="truncate text-sm">{f.name}</span>
                <span className="shrink-0 text-xs text-white/40">
                  {(f.size / 1024 / 1024).toFixed(1)} MB
                </span>
              </div>
              <button
                type="button"
                aria-label="remove"
                className="rounded-md p-1 text-white/40 hover:bg-white/5 hover:text-white"
                onClick={() => onChange(files.filter((_, idx) => idx !== i))}
              >
                <X className="h-4 w-4" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
