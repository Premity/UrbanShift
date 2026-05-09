import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion, useReducedMotion } from "framer-motion";
import { Briefcase, Home, Sparkles, Loader2 } from "lucide-react";
import { Header } from "../components/shared/Header";
import { ChatTurn } from "../components/intake/ChatTurn";
import { TurnInputRenderer } from "../components/intake/TurnInputRenderer";
import { ResumeUploader } from "../components/intake/ResumeUploader";
import { sendTurn, startSession, type Turn, type TurnResponse, type ResumeParseResponse } from "../lib/intake";


// Multi-field turns: the API turn `field` is the primary key,
// but the answer value must be a dict with all sibling fields.
// This map tells us which secondary fields to collect alongside the primary.
const COMBINED_FIELDS: Record<string, string[]> = {
  native_lang: ["native_lang", "languages_spoken"],
  origin_state: ["origin_state", "migrant_status"],
  age: ["age", "gender"],
  sector: ["sector", "skills"],
  education: ["education", "years_experience"],
  employment_status: ["employment_status", "income_range_inr"],
  budget_inr: ["budget_inr", "preferred_areas", "occupancy_pref"],
};

interface Message {
  id: number;
  role: "agent" | "user";
  // Agent messages carry one of:
  i18nKey?: string;                          // static key e.g. "intake.seekerType.label"
  promptI18n?: Record<string, string>;       // turn prompt map from backend
  // User messages carry:
  rawValue?: unknown;                        // original answer value
  field?: string;                            // primary field name
  // Fallback for anything that doesn't fit above:
  text?: string;
}

interface SeekerSelectProps {
  onSelect: (type: "job" | "housing" | "both") => void;
}

const SEEKER_ICONS = {
  job: Briefcase,
  housing: Home,
  both: Sparkles,
} as const;

function SeekerSelect({ onSelect }: SeekerSelectProps) {
  const { t } = useTranslation();
  const reducedMotion = useReducedMotion();
  const options: { key: "job" | "housing" | "both" }[] = [
    { key: "job" },
    { key: "housing" },
    { key: "both" },
  ];

  return (
    <div className="space-y-3" role="group" aria-label={t("intake.seekerType.label")}>
      {options.map(({ key }) => {
        const Icon = SEEKER_ICONS[key];
        return (
          <motion.button
            key={key}
            whileTap={reducedMotion ? undefined : { scale: 0.97 }}
            onClick={() => onSelect(key)}
            className="w-full min-h-[56px] flex items-center gap-3 px-5 py-3 rounded-2xl border border-border bg-background hover:border-primary hover:text-primary transition-colors duration-150 text-left font-medium cursor-pointer"
          >
            <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
            <span>{t(`intake.seekerType.${key}`)}</span>
          </motion.button>
        );
      })}
    </div>
  );
}

export default function IntakePage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const bottomRef = useRef<HTMLDivElement>(null);
  const reducedMotion = useReducedMotion();

  const [sessionReady, setSessionReady] = useState(false);
  const [seekerType, setSeekerType] = useState<string | null>(null);
  const [showResumePrompt, setShowResumePrompt] = useState(false);
  const [currentTurn, setCurrentTurn] = useState<Turn | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const msgCounter = useRef(0);
  const [loading, setLoading] = useState(false);
  const [turnIndex, setTurnIndex] = useState(0);
  const totalTurns = seekerType === "job" ? 7 : 8;

  function addAgentKey(i18nKey: string) {
    msgCounter.current += 1;
    setMessages((prev) => [...prev, { id: msgCounter.current, role: "agent", i18nKey }]);
  }

  function addAgentTurn(promptI18n: Record<string, string>) {
    msgCounter.current += 1;
    setMessages((prev) => [...prev, { id: msgCounter.current, role: "agent", promptI18n }]);
  }

  function addUserMessage(rawValue: unknown, field: string) {
    msgCounter.current += 1;
    setMessages((prev) => [...prev, { id: msgCounter.current, role: "user", rawValue, field }]);
  }

  useEffect(() => {
    startSession(i18n.language)
      .then(() => setSessionReady(true))
      .catch(console.error);
  }, [i18n.language]);

  useEffect(() => {
    if (sessionReady && !seekerType) {
      addAgentKey("intake.seekerType.label");
    }
  }, [sessionReady]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSeekerSelect(type: "job" | "housing" | "both") {
    setSeekerType(type);
    addUserMessage(type, "seeker_type");

    // For job/both seekers: ask about resume before starting chat turns
    if (type === "job" || type === "both") {
      // Send the seeker_type turn to the backend in the background so
      // the session is primed; we'll show the resume prompt next.
      sendTurn({ field: "seeker_type", value: type }).catch(console.error);
      setShowResumePrompt(true);
      return;
    }

    // housing-only: skip resume prompt, go straight to chat
    setLoading(true);
    try {
      const res = await sendTurn({ field: "seeker_type", value: type });
      handleTurnResponse(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  function handleResumeParsed(result: ResumeParseResponse) {
    // Navigate directly to the Confirm screen with parsed fields + metadata
    navigate("/intake/confirm", {
      state: {
        profile: {
          seeker_type: seekerType,
          current_city: "Bengaluru",
          ...result.profile,
        },
        resumeMissingFields: result.missing_fields,
      },
    });
  }

  async function handleResumeSkip() {
    // Continue with normal chat turn flow
    setShowResumePrompt(false);
    setLoading(true);
    try {
      // Request the first turn (seeker_type already sent, so backend will
      // return the next question directly)
      const res = await sendTurn(undefined);
      handleTurnResponse(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }



  function handleTurnResponse(res: TurnResponse) {
    if (res.complete) {
      navigate("/intake/confirm", { state: { profile: res.current_profile } });
      return;
    }
    if (res.turn) {
      addAgentTurn(res.turn.prompt_i18n);
      setCurrentTurn(res.turn);
      setTurnIndex((i) => i + 1);
    }
  }

  async function handleAnswer(value: unknown) {
    if (!currentTurn) return;

    // Build the dict answer for combined-field turns
    const fields = COMBINED_FIELDS[currentTurn.field];
    let answerValue: unknown;

    if (fields && fields.length > 1) {
      if (typeof value === "object" && value !== null && !Array.isArray(value)) {
        answerValue = value;
      } else {
        const dict: Record<string, unknown> = {};
        dict[fields[0]] = value;
        for (let i = 1; i < fields.length; i++) {
          dict[fields[i]] = Array.isArray(value) ? value : null;
        }
        answerValue = dict;
      }
    } else {
      answerValue = value;
    }

    addUserMessage(value, currentTurn.field);


    setCurrentTurn(null);
    setLoading(true);
    try {
      const res = await sendTurn({ field: currentTurn.field, value: answerValue });
      handleTurnResponse(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  const progressPct = Math.round((turnIndex / totalTurns) * 100);

  return (
    <div className="min-h-dvh flex flex-col bg-background">
      <Header />

      {/* Progress bar */}
      {seekerType && (
        <div
          className="h-1 bg-muted sticky top-14 z-40"
          role="progressbar"
          aria-valuenow={progressPct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={t("intake.progress")}
        >
          <motion.div
            className="h-full bg-primary"
            initial={reducedMotion ? false : { width: 0 }}
            animate={{ width: `${progressPct}%` }}
            transition={{ duration: 0.4 }}
          />
        </div>
      )}

      {/* Chat area */}
      <main className="flex-1 flex flex-col max-w-[600px] w-full mx-auto px-4 py-6 gap-3">
        {messages.map((msg) => {
          // Resolve display text reactively from current language
          let text = msg.text ?? "";
          if (msg.i18nKey) {
            text = t(msg.i18nKey);
          } else if (msg.promptI18n) {
            const lang = i18n.language as keyof typeof msg.promptI18n;
            text = msg.promptI18n[lang] ?? msg.promptI18n.en ?? "";
          } else if (msg.role === "user" && msg.rawValue !== undefined && msg.field) {
            const value = msg.rawValue;
            if (msg.field === "seeker_type") {
              text = t(`intake.seekerType.${String(value)}`, String(value));
            } else if (typeof value === "object" && value !== null && !Array.isArray(value)) {
              const parts = Object.entries(value as Record<string, unknown>)
                .filter(([_, v]) => v !== null && v !== "" && !(Array.isArray(v) && (v as unknown[]).length === 0))
                .map(([k, v]) => {
                  if (Array.isArray(v) && v.length === 2 && typeof v[0] === "number") {
                    const prefix = k.endsWith("_inr") ? "₹" : "";
                    return `${t(`confirm.${k}`, k)}: ${prefix}${(v[0] as number).toLocaleString()} – ${prefix}${(v[1] as number).toLocaleString()}`;
                  }
                  if (typeof v === "number") {
                    const prefix = k.endsWith("_inr") ? "₹" : "";
                    return `${t(`confirm.${k}`, k)}: ${prefix}${v.toLocaleString()}`;
                  }
                  if (Array.isArray(v))
                    return `${t(`confirm.${k}`, k)}: ${(v as string[]).map(x => t(`intake.options.${x}`, x)).join(", ")}`;
                  return `${t(`confirm.${k}`, k)}: ${t(`intake.options.${String(v)}`, String(v))}`;
                });
              text = parts.join(" | ");
            } else {
              text = Array.isArray(value)
                ? (value as string[]).map(x => t(`intake.options.${x}`, x)).join(", ")
                : t(`intake.options.${String(value)}`, String(value));
            }
          }
          return <ChatTurn key={msg.id} role={msg.role} text={text} />;
        })}

        {loading && (
          <motion.div
            initial={reducedMotion ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex justify-start"
          >
            <div
              className="bg-muted rounded-2xl rounded-tl-sm px-4 py-3"
              role="status"
              aria-label={t("intake.loading")}
            >
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" aria-hidden="true" />
            </div>
          </motion.div>
        )}

        <div ref={bottomRef} />
      </main>

      {/* Sticky input */}
      <div className="sticky bottom-0 border-t border-border bg-background/95 backdrop-blur">
        <div className="max-w-[600px] mx-auto px-4 py-4">
          {sessionReady && !seekerType && (
            <SeekerSelect onSelect={handleSeekerSelect} />
          )}
          {showResumePrompt && (
            <ResumeUploader
              onParsed={handleResumeParsed}
              onSkip={handleResumeSkip}
            />
          )}
          {currentTurn && !loading && !showResumePrompt && (
            <TurnInputRenderer
              turn={currentTurn}
              onSubmit={handleAnswer}
              disabled={loading}
            />
          )}
        </div>
      </div>

    </div>
  );
}
