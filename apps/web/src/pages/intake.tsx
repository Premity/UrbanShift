import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion, useReducedMotion } from "framer-motion";
import { Briefcase, Home, Sparkles, Loader2 } from "lucide-react";
import { Header } from "../components/shared/Header";
import { ChatTurn } from "../components/intake/ChatTurn";
import { TurnInputRenderer } from "../components/intake/TurnInputRenderer";
import { sendTurn, startSession, type Turn, type TurnResponse } from "../lib/intake";

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
  text: string;
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
  const [currentTurn, setCurrentTurn] = useState<Turn | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const msgCounter = useRef(0);
  const [loading, setLoading] = useState(false);
  const [turnIndex, setTurnIndex] = useState(0);
  const totalTurns = seekerType === "job" ? 7 : 8;

  function addMessage(role: "agent" | "user", text: string) {
    msgCounter.current += 1;
    const id = msgCounter.current;
    setMessages((prev) => [...prev, { id, role, text }]);
  }

  useEffect(() => {
    startSession(i18n.language)
      .then(() => setSessionReady(true))
      .catch(console.error);
  }, [i18n.language]);

  useEffect(() => {
    if (sessionReady && !seekerType) {
      addMessage("agent", t("intake.seekerType.label"));
    }
  }, [sessionReady]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSeekerSelect(type: "job" | "housing" | "both") {
    setSeekerType(type);
    addMessage("user", t(`intake.seekerType.${type}`));
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

  function handleTurnResponse(res: TurnResponse) {
    if (res.complete) {
      navigate("/intake/confirm", { state: { profile: res.current_profile } });
      return;
    }
    if (res.turn) {
      const lang = i18n.language as keyof typeof res.turn.prompt_i18n;
      const prompt = res.turn.prompt_i18n[lang] ?? res.turn.prompt_i18n.en;
      addMessage("agent", prompt);
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
      // For combined turns the value from TurnInputRenderer is the primary field's value.
      // We wrap it in an object; secondary fields default to empty / the same value.
      const dict: Record<string, unknown> = {};
      dict[fields[0]] = value;
      // Secondary fields: for multi/chips with free text they come through as the same value;
      // the backend is lenient — empty arrays/nulls are fine for optional secondary fields.
      for (let i = 1; i < fields.length; i++) {
        dict[fields[i]] = Array.isArray(value) ? value : null;
      }
      answerValue = dict;
    } else {
      answerValue = value;
    }

    // Show user's answer as a readable string
    const displayText = Array.isArray(value)
      ? (value as string[]).join(", ")
      : String(value);
    addMessage("user", displayText);

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
          className="h-1 bg-muted"
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
        {messages.map((msg) => (
          <ChatTurn key={msg.id} role={msg.role} text={msg.text} />
        ))}

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
          {currentTurn && !loading && (
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
