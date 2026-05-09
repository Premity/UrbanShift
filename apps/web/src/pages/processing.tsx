import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion, useReducedMotion } from "framer-motion";
import { ExternalLink } from "lucide-react";
import { Header } from "../components/shared/Header";

const AGENT_STEPS = [
  { key: "orchestrator", label: "Orchestrator" },
  { key: "scheme", label: "Schemes" },
  { key: "job", label: "Jobs" },
  { key: "housing", label: "Housing" },
  { key: "validator", label: "Validator" },
  { key: "merge", label: "Merge" },
] as const;

type AgentKey = (typeof AGENT_STEPS)[number]["key"];
type StepStatus = "pending" | "running" | "complete";

interface StepMeta {
  kept?: number;
  filtered?: number;
  langsmithUrl?: string;
}

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const STALL_TIMEOUT_MS = 3000;
// Minimum visible time per step so users perceive progress even when the
// graph runs in <1s. Without this, every step would flash green simultaneously.
const MIN_STEP_VISIBLE_MS = 350;

export default function ProcessingPage() {
  const { t } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const reduced = useReducedMotion();

  const profile = (location.state as { profile?: Record<string, unknown> })?.profile;
  const seekerType = (profile?.seeker_type as string) ?? "both";

  const [stepStatuses, setStepStatuses] = useState<Record<AgentKey, StepStatus>>(() => {
    const init = {} as Record<AgentKey, StepStatus>;
    AGENT_STEPS.forEach((s) => { init[s.key] = "pending"; });
    return init;
  });
  const [stepMeta, setStepMeta] = useState<Partial<Record<AgentKey, StepMeta>>>({});
  const [stalled, setStalled] = useState(false);
  const [langsmithUrl, setLangsmithUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const stallTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Visible steps — omit housing/job when seeker_type is job/housing respectively
  const visibleSteps = AGENT_STEPS.filter((s) => {
    if (s.key === "housing" && seekerType === "job") return false;
    if (s.key === "job" && seekerType === "housing") return false;
    return true;
  });

  useEffect(() => {
    const abortController = new AbortController();

    // Start stall timer — show skeleton if no events arrive within STALL_TIMEOUT_MS
    stallTimerRef.current = setTimeout(() => setStalled(true), STALL_TIMEOUT_MS);

    function resetStallTimer() {
      if (stallTimerRef.current) clearTimeout(stallTimerRef.current);
      setStalled(false);
    }

    function markStep(agent: AgentKey, status: StepStatus, meta?: StepMeta) {
      resetStallTimer();
      setStepStatuses((prev) => ({ ...prev, [agent]: status }));
      if (meta && Object.keys(meta).length > 0) {
        setStepMeta((prev) => ({ ...prev, [agent]: meta }));
      }
    }

    // Apply incoming agent_step events with a minimum visible time per step
    // so the UI shows a perceptible progression even when the backend is fast.
    const stepQueue: Array<{ agent: AgentKey; status: StepStatus; meta?: StepMeta }> = [];
    let stepDrainPromise: Promise<void> | null = null;

    async function drainStepQueue() {
      while (stepQueue.length > 0) {
        const next = stepQueue.shift()!;
        markStep(next.agent, next.status, next.meta);
        // Only delay on "running" → keeps the running pulse visible.
        if (next.status === "running") {
          await new Promise((res) => setTimeout(res, MIN_STEP_VISIBLE_MS));
        }
      }
      stepDrainPromise = null;
    }

    function enqueueStep(agent: AgentKey, status: StepStatus, meta?: StepMeta) {
      stepQueue.push({ agent, status, meta });
      if (!stepDrainPromise) {
        stepDrainPromise = drainStepQueue();
      }
    }

    async function streamGraph() {
      try {
        const response = await fetch(`${API_BASE}/api/run`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
          signal: abortController.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder("utf-8");

        if (!reader) {
          throw new Error("No response body reader");
        }

        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Process SSE lines
          const lines = buffer.split('\n');
          buffer = lines.pop() || ""; // Keep the last incomplete line in buffer

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const dataStr = line.substring(6).trim();
              if (!dataStr) continue;

              try {
                const data = JSON.parse(dataStr);
                if (data.type === "agent_step") {
                  const status: StepStatus = data.status === "running" ? "running" : "complete";
                  const meta: StepMeta = {};
                  if (data.kept !== undefined) meta.kept = data.kept;
                  if (data.filtered !== undefined) meta.filtered = data.filtered;
                  if (data.langsmith_url) meta.langsmithUrl = data.langsmith_url;
                  enqueueStep(data.agent as AgentKey, status, meta);
                }
                if (data.type === "plan") {
                  if (data.langsmith_url) setLangsmithUrl(data.langsmith_url);
                  resetStallTimer();
                  // Let queued steps finish animating before we navigate.
                  if (stepDrainPromise) await stepDrainPromise;
                  navigate("/results", { state: { plan: data.plan, profile } });
                  return;
                }
                if (data.type === "error") {
                  resetStallTimer();
                  setError(data.message || t("processing.error", "Something went wrong. Please try again."));
                  return;
                }
                if (data.type === "done") {
                  resetStallTimer();
                  return;
                }
              } catch (e) {
                // Ignore parsing errors for partial/invalid chunks
              }
            }
          }
        }
      } catch (err: any) {
        if (err.name === 'AbortError') return;
        setError(t("processing.error", "Something went wrong. Please try again."));
      }
    }

    streamGraph();

    return () => {
      if (stallTimerRef.current) clearTimeout(stallTimerRef.current);
      abortController.abort();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-dvh flex flex-col bg-background">
      <Header />

      <main className="flex-1 flex flex-col items-center justify-center max-w-[600px] w-full mx-auto px-4 py-16 gap-10">
        <motion.div
          initial={reduced ? false : { opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
          className="text-center space-y-2"
        >
          <h1 className="text-2xl font-bold text-foreground">
            {t("processing.title", "Finding your plan…")}
          </h1>
          <p className="text-sm text-muted-foreground">
            {t("processing.subtitle", "Our agents are searching across jobs, schemes, and housing.")}
          </p>
        </motion.div>

        {/* Stall skeleton — shown when SSE hasn't arrived within 3s */}
        {stalled && !error && (
          <motion.div
            initial={reduced ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            className="w-full flex flex-col gap-3"
            aria-label="Loading"
          >
            {[...Array(visibleSteps.length)].map((_, i) => (
              <div
                key={i}
                className="h-[46px] rounded-xl border border-border bg-muted/40 animate-pulse"
                style={{ animationDelay: `${i * 80}ms` }}
              />
            ))}
          </motion.div>
        )}

        {/* Agent step indicators */}
        {!stalled && (
          <div className="w-full flex flex-col gap-3">
            {visibleSteps.map((step, i) => {
              const status = stepStatuses[step.key];
              const meta = stepMeta[step.key];
              return (
                <motion.div
                  key={step.key}
                  initial={reduced ? false : { opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.07, duration: 0.3 }}
                  className={`flex items-center gap-3 rounded-xl border px-4 py-3 transition-colors duration-300 ${
                    status === "complete"
                      ? "border-primary/40 bg-primary/5"
                      : status === "running"
                      ? "border-primary/60 bg-primary/10"
                      : "border-border bg-background"
                  }`}
                >
                  {/* Status dot */}
                  <span
                    aria-hidden="true"
                    className={`w-2.5 h-2.5 rounded-full shrink-0 transition-colors duration-300 ${
                      status === "complete"
                        ? "bg-primary"
                        : status === "running"
                        ? "bg-primary animate-pulse"
                        : "bg-muted-foreground/30"
                    }`}
                  />
                  <span
                    className={`text-sm font-medium transition-colors duration-300 ${
                      status === "pending" ? "text-muted-foreground" : "text-foreground"
                    }`}
                  >
                    {step.label}
                  </span>

                  {/* Validator kept/filtered counts */}
                  {status === "complete" && step.key === "validator" && meta && (
                    <span className="ml-auto text-xs text-muted-foreground">
                      kept {meta.kept ?? 0} / filtered {meta.filtered ?? 0}
                    </span>
                  )}

                  {/* Generic done marker for non-validator steps */}
                  {status === "complete" && step.key !== "validator" && (
                    <motion.span
                      initial={reduced ? false : { scale: 0 }}
                      animate={{ scale: 1 }}
                      className="ml-auto text-xs font-medium text-primary"
                    >
                      ✓ Done
                    </motion.span>
                  )}

                  {/* LangSmith link per step (when available) */}
                  {status === "complete" && meta?.langsmithUrl && (
                    <a
                      href={meta.langsmithUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="ml-2 text-xs text-muted-foreground hover:text-foreground inline-flex items-center gap-0.5"
                      aria-label="View trace in LangSmith"
                    >
                      Trace <ExternalLink className="w-3 h-3" />
                    </a>
                  )}

                  {status === "running" && (
                    <span className="ml-auto text-xs text-muted-foreground animate-pulse">Running…</span>
                  )}
                </motion.div>
              );
            })}
          </div>
        )}

        {/* Plan-level LangSmith trace link */}
        {langsmithUrl && (
          <a
            href={langsmithUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
          >
            View trace <ExternalLink className="w-3 h-3" />
          </a>
        )}

        {error && (
          <div role="alert" className="w-full rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3">
            <p className="text-sm text-destructive">{error}</p>
            <button
              onClick={() => navigate("/intake/confirm", { state: { profile } })}
              className="mt-2 text-sm font-medium text-destructive underline underline-offset-2 cursor-pointer"
            >
              {t("processing.go_back", "Go back and try again")}
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
