/**
 * 简历上传组件 —— 简洁风格
 */

"use client";

import { uploadResume } from "@/lib/api";
import { useInterviewStore } from "@/store/useInterviewStore";
import { CheckCircle2, Loader2, Upload } from "lucide-react";
import { useCallback, useRef, useState } from "react";

export default function ResumeUploader() {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { resumeId, resumeFilename, setResume } = useInterviewStore();

  const handleFile = useCallback(async (file: File) => {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("仅支持 PDF 格式文件");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError("文件大小不能超过 10MB");
      return;
    }

    setError("");
    setIsUploading(true);

    try {
      const result = await uploadResume(file);
      setResume(result.resume_id, result.filename);
    } catch (err) {
      setError(err instanceof Error ? err.message : "上传失败，请重试");
    } finally {
      setIsUploading(false);
    }
  }, [setResume]);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  // 上传成功
  if (resumeId) {
    return (
      <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-100">
            <CheckCircle2 className="h-5 w-5 text-emerald-600" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-emerald-800">简历已上传</p>
            <p className="truncate text-xs text-emerald-600">
              {resumeFilename}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div
        className={`relative cursor-pointer rounded-xl border-2 border-dashed px-6 py-8 text-center transition-all ${
          isDragging
            ? "border-brand-700/40 bg-brand-700/4"
            : "border-black/8 bg-white hover:border-brand-700/25 hover:bg-brand-700/2"
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        {isUploading ? (
          <div>
            <Loader2 className="mx-auto mb-2.5 h-8 w-8 animate-spin text-brand-700" />
            <p className="text-sm text-ink-secondary">正在解析简历...</p>
          </div>
        ) : (
          <div>
            <div className="mx-auto mb-2.5 flex h-10 w-10 items-center justify-center rounded-2xl bg-brand-700/8">
              <Upload className="h-5 w-5 text-brand-700" />
            </div>
            <p className="text-sm font-medium text-ink-primary">
              拖拽或点击上传简历
            </p>
            <p className="mt-1 text-xs text-ink-tertiary">
              支持 PDF 格式，最大 10MB
            </p>
          </div>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={onFileChange}
        />
      </div>

      {error && (
        <p className="mt-2 text-center text-xs text-red-500">{error}</p>
      )}
    </div>
  );
}
