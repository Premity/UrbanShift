import { BrowserRouter, Routes, Route, useNavigate } from "react-router-dom";
import { Header } from "./components/shared/Header";
import { useTranslation } from "react-i18next";
import { motion, useReducedMotion } from "framer-motion";
import { Briefcase, Home, Sparkles, ArrowRight, MapPin, Users, ShieldCheck } from "lucide-react";
import IntakePage from "./pages/intake";
import ConfirmPage from "./pages/confirm";
import ProcessingPage from "./pages/processing";
import ResultsPage from "./pages/results";

const SEEKER_PILLS = [
  { key: "job", Icon: Briefcase },
  { key: "housing", Icon: Home },
  { key: "both", Icon: Sparkles },
] as const;

const TRUST_ITEMS = [
  { Icon: MapPin, key: "trust_states" },
  { Icon: Users, key: "trust_users" },
  { Icon: ShieldCheck, key: "trust_free" },
] as const;

function SunArc({ reduced }: { reduced: boolean | null }) {
  return (
    <svg
      aria-hidden="true"
      className="absolute inset-0 w-full h-full pointer-events-none"
      viewBox="0 0 800 600"
      preserveAspectRatio="xMidYMid slice"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <radialGradient id="sunGlow" cx="50%" cy="110%" r="70%">
          <stop offset="0%" stopColor="hsl(24.6 95% 53.1%)" stopOpacity="0.18" />
          <stop offset="60%" stopColor="hsl(38 95% 62%)" stopOpacity="0.06" />
          <stop offset="100%" stopColor="transparent" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="arcGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="hsl(24.6 95% 53.1%)" stopOpacity="0.5" />
          <stop offset="100%" stopColor="hsl(24.6 95% 53.1%)" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* Ambient warmth wash */}
      <ellipse cx="400" cy="700" rx="500" ry="360" fill="url(#sunGlow)" />

      {/* Outer slow arc */}
      <motion.circle
        cx="400" cy="580" r="320"
        fill="none"
        stroke="hsl(24.6 95% 53.1%)"
        strokeWidth="1"
        strokeOpacity="0.12"
        strokeDasharray="20 14"
        animate={reduced ? {} : { rotate: 360 }}
        transition={{ duration: 120, repeat: Infinity, ease: "linear" }}
        style={{ transformOrigin: "400px 580px" }}
      />

      {/* Mid arc */}
      <motion.circle
        cx="400" cy="580" r="240"
        fill="none"
        stroke="hsl(24.6 95% 53.1%)"
        strokeWidth="1.5"
        strokeOpacity="0.18"
        strokeDasharray="6 22"
        animate={reduced ? {} : { rotate: -360 }}
        transition={{ duration: 80, repeat: Infinity, ease: "linear" }}
        style={{ transformOrigin: "400px 580px" }}
      />

      {/* Inner bright ring */}
      <motion.circle
        cx="400" cy="580" r="160"
        fill="none"
        stroke="hsl(24.6 95% 53.1%)"
        strokeWidth="2"
        strokeOpacity="0.28"
        strokeDasharray="3 9"
        animate={reduced ? {} : { rotate: 360 }}
        transition={{ duration: 45, repeat: Infinity, ease: "linear" }}
        style={{ transformOrigin: "400px 580px" }}
      />

      {/* Pulsing core dot */}
      <motion.circle
        cx="400" cy="580" r="8"
        fill="hsl(24.6 95% 53.1%)"
        fillOpacity="0.4"
        animate={reduced ? {} : { scale: [1, 1.75, 1], fillOpacity: [0.4, 0.15, 0.4] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        style={{ transformOrigin: "400px 580px" }}
      />
    </svg>
  );
}

function LandingPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const reduced = useReducedMotion();

  const containerVariants = {
    hidden: {},
    show: { transition: { staggerChildren: 0.12 } },
  };
  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] } },
  };

  return (
    <div className="min-h-dvh flex flex-col bg-background text-foreground overflow-hidden">
      <Header />

      <main className="flex-1 relative flex flex-col items-center justify-center px-4 py-16 sm:py-24">
        <SunArc reduced={reduced} />

        <motion.div
          variants={containerVariants}
          initial={reduced ? "show" : "hidden"}
          animate="show"
          className="relative z-10 flex flex-col items-center text-center max-w-2xl gap-6"
        >
          {/* Eyebrow */}
          <motion.div variants={itemVariants}>
            <span className="inline-flex items-center gap-2 text-xs font-semibold tracking-widest uppercase text-primary border border-primary/30 rounded-full px-4 py-1.5 bg-primary/5">
              <MapPin className="h-3 w-3" aria-hidden="true" />
              {t("landing.eyebrow", "For India's Urban Migrants")}
            </span>
          </motion.div>

          {/* Headline */}
          <motion.div variants={itemVariants} className="space-y-2">
            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight leading-[1.05] text-foreground">
              {t("landing.headline_1", "Find Work.")}
            </h1>
            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight leading-[1.05] text-primary">
              {t("landing.headline_2", "Find Home.")}
            </h1>
            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight leading-[1.05] text-foreground">
              {t("landing.headline_3", "Find Schemes.")}
            </h1>
          </motion.div>

          {/* Subtitle */}
          <motion.p
            variants={itemVariants}
            className="text-lg text-muted-foreground max-w-md leading-relaxed"
          >
            {t("landing.subtitle", "AI-powered guidance for urban migrant workers — in your language, in minutes.")}
          </motion.p>

          {/* CTA */}
          <motion.div variants={itemVariants}>
            <button
              onClick={() => navigate("/intake")}
              className="group inline-flex items-center gap-3 min-h-[52px] px-8 rounded-2xl bg-primary text-primary-foreground font-semibold text-base hover:bg-primary/90 active:scale-[0.97] transition-all duration-150 cursor-pointer shadow-lg shadow-primary/25"
            >
              {t("landing.getStarted", "Get Started")}
              <ArrowRight
                className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-1"
                aria-hidden="true"
              />
            </button>
          </motion.div>

          {/* Seeker type pills */}
          <motion.div
            variants={itemVariants}
            className="flex items-center gap-2 flex-wrap justify-center"
          >
            {SEEKER_PILLS.map(({ key, Icon }) => (
              <span
                key={key}
                className="inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1 text-xs font-medium text-muted-foreground bg-muted"
              >
                <Icon className="h-3 w-3 text-primary" aria-hidden="true" />
                {t(`landing.seekerType.${key}`)}
              </span>
            ))}
          </motion.div>

          {/* Trust row */}
          <motion.div
            variants={itemVariants}
            className="flex items-center gap-6 flex-wrap justify-center pt-2"
          >
            {TRUST_ITEMS.map(({ Icon, key }) => (
              <div key={key} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Icon className="h-3.5 w-3.5 text-secondary" aria-hidden="true" />
                <span>{t(`landing.${key}`, key)}</span>
              </div>
            ))}
          </motion.div>
        </motion.div>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/intake" element={<IntakePage />} />
        <Route path="/intake/confirm" element={<ConfirmPage />} />
        <Route path="/processing" element={<ProcessingPage />} />
        <Route path="/results" element={<ResultsPage />} />
      </Routes>
    </BrowserRouter>
  );
}

