import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion, useReducedMotion } from "framer-motion";
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

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

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
  const [error, setError] = useState<string | null>(null);

  // Visible steps — omit housing/job when seeker_type is job/housing respectively
  const visibleSteps = AGENT_STEPS.filter((s) => {
    if (s.key === "housing" && seekerType === "job") return false;
    if (s.key === "job" && seekerType === "housing") return false;
    return true;
  });

  useEffect(() => {
    const es = new EventSource(`${API_BASE}/api/run`, {
      // credentials need to be set differently for EventSource; we pass session via cookie
    });

    function markStep(agent: AgentKey, status: StepStatus) {
      setStepStatuses((prev) => ({ ...prev, [agent]: status }));
    }

    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === "agent_step") {
          markStep(data.agent as AgentKey, data.status === "running" ? "running" : "complete");
        }
        if (data.type === "plan") {
          es.close();
          navigate("/results", { state: { plan: data.plan, profile } });
        }
        if (data.type === "done") {
          es.close();
        }
      } catch {
        // non-JSON message — ignore
      }
    };

    es.onerror = () => {
      es.close();
      setError(t("processing.error", "Something went wrong. Please try again."));
    };

    // POST /api/run to kick off the graph (EventSource is GET-only; backend fires SSE on this endpoint)
    // Per PRD §7.1, /api/run accepts POST and returns SSE stream.
    // We trigger it as a POST separately, then SSE picks up progress.
    fetch(`${API_BASE}/api/run`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    }).catch(() => {
      es.close();
      setError(t("processing.error", "Failed to start processing."));
    });

    return () => es.close();
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

        {/* Agent step indicators */}
        <div className="w-full flex flex-col gap-3">
          {visibleSteps.map((step, i) => {
            const status = stepStatuses[step.key];
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
                {status === "complete" && (
                  <motion.span
                    initial={reduced ? false : { scale: 0 }}
                    animate={{ scale: 1 }}
                    className="ml-auto text-xs font-medium text-primary"
                  >
                    ✓ Done
                  </motion.span>
                )}
                {status === "running" && (
                  <span className="ml-auto text-xs text-muted-foreground animate-pulse">Running…</span>
                )}
              </motion.div>
            );
          })}
        </div>

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
