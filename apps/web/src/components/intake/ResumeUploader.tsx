import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { motion, useReducedMotion } from "framer-motion";
import { Upload, FileText, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { parseResume, type ResumeParseResponse } from "../../lib/intake";

interface ResumeUploaderProps {
  onParsed: (result: ResumeParseResponse) => void;
  onSkip: () => void;
}

type UploadState = "idle" | "dragging" | "uploading" | "success" | "error";

export function ResumeUploader({ onParsed, onSkip }: ResumeUploaderProps) {
  const { t } = useTranslation();
  const reducedMotion = useReducedMotion();
  const inputRef = useRef<HTMLInputElement>(null);
  const [state, setState] = useState<UploadState>("idle");
  const [errorKey, setErrorKey] = useState<string | null>(null);

  function _resolveErrorKey(detail: string): string {
    // Map API error detail strings → i18n keys
    const map: Record<string, string> = {
      "resume.error_too_large": "resume.error_too_large",
      "resume.error_unsupported_type": "resume.error_unsupported_type",
      "resume.error_parse": "resume.error_parse",
      "resume.error_no_text": "resume.error_no_text",
    };
    for (const [k, v] of Object.entries(map)) {
      if (detail.includes(k)) return v;
    }
    return "resume.error_parse";
  }

  async function handleFile(file: File) {
    // Client-side size guard
    if (file.size > 5 * 1024 * 1024) {
      setState("error");
      setErrorKey("resume.error_too_large");
      return;
    }
    // Client-side type guard
    const name = file.name.toLowerCase();
    if (!name.endsWith(".pdf") && !name.endsWith(".docx")) {
      setState("error");
      setErrorKey("resume.error_unsupported_type");
      return;
    }

    setState("uploading");
    setErrorKey(null);
    try {
      const result = await parseResume(file);
      setState("success");
      // Short delay so the success state is visible, then hand off
      setTimeout(() => onParsed(result), 900);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "";
      setState("error");
      setErrorKey(_resolveErrorKey(msg));
    }
  }

  function onInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    // Reset the input so the same file can be re-uploaded after error
    e.target.value = "";
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setState("idle");
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  }

  const isDragging = state === "dragging";
  const isUploading = state === "uploading";
  const isSuccess = state === "success";
  const isError = state === "error";

  return (
    <motion.div
      initial={reducedMotion ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="rounded-2xl border border-border bg-background overflow-hidden"
    >
      {/* Header */}
      <div className="px-5 pt-5 pb-4">
        <p className="text-sm font-semibold text-foreground">{t("resume.cta_title")}</p>
        <p className="text-xs text-muted-foreground mt-0.5">{t("resume.cta_subtitle")}</p>
      </div>

      {/* Drop zone */}
      <div
        className={`mx-4 mb-4 rounded-xl border-2 border-dashed transition-colors duration-150 ${
          isDragging
            ? "border-primary bg-primary/5"
            : isSuccess
              ? "border-green-500 bg-green-500/5"
              : isError
                ? "border-destructive bg-destructive/5"
                : "border-border bg-muted/30"
        }`}
        onDragOver={(e) => { e.preventDefault(); if (!isUploading) setState("dragging"); }}
        onDragLeave={() => { if (state === "dragging") setState("idle"); }}
        onDrop={onDrop}
      >
        <button
          type="button"
          disabled={isUploading || isSuccess}
          onClick={() => inputRef.current?.click()}
          className="w-full flex flex-col items-center gap-3 px-4 py-6 cursor-pointer disabled:cursor-default focus:outline-none"
          aria-label={t("resume.browse")}
        >
          {isUploading ? (
            <>
              <Loader2 className="h-7 w-7 text-primary animate-spin" aria-hidden="true" />
              <span className="text-sm text-muted-foreground">{t("resume.uploading")}</span>
            </>
          ) : isSuccess ? (
            <>
              <CheckCircle2 className="h-7 w-7 text-green-500" aria-hidden="true" />
              <span className="text-sm font-medium text-green-600">{t("resume.success")}</span>
            </>
          ) : isError ? (
            <>
              <AlertCircle className="h-7 w-7 text-destructive" aria-hidden="true" />
              <span className="text-sm text-destructive text-center">
                {t(errorKey ?? "resume.error_parse")}
              </span>
              <span className="text-xs text-muted-foreground underline">{t("resume.browse")}</span>
            </>
          ) : (
            <>
              {isDragging ? (
                <Upload className="h-7 w-7 text-primary" aria-hidden="true" />
              ) : (
                <FileText className="h-7 w-7 text-muted-foreground" aria-hidden="true" />
              )}
              <div className="text-center space-y-1">
                <p className="text-sm text-foreground">
                  {isDragging ? t("resume.drop_hint") : t("resume.browse")}
                </p>
                <p className="text-xs text-muted-foreground">{t("resume.size_limit")}</p>
              </div>
            </>
          )}
        </button>

        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          className="sr-only"
          onChange={onInputChange}
          aria-hidden="true"
        />
      </div>

      {/* Skip */}
      {!isSuccess && (
        <div className="px-4 pb-4">
          <button
            type="button"
            onClick={onSkip}
            disabled={isUploading}
            className="w-full text-sm text-muted-foreground hover:text-foreground transition-colors duration-150 py-2 disabled:opacity-40 cursor-pointer disabled:cursor-default"
          >
            {t("resume.skip_btn")}
          </button>
        </div>
      )}
    </motion.div>
  );
}
