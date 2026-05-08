import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion, useReducedMotion } from "framer-motion";
import { Loader2 } from "lucide-react";
import { Header } from "../components/shared/Header";
import { finalize } from "../lib/intake";

interface ProfileRow {
  label: string;
  value: string;
}

function profileRows(profile: Record<string, unknown>, t: (k: string) => string): ProfileRow[] {
  const rows: ProfileRow[] = [];
  const add = (key: string, val: unknown) => {
    if (val === undefined || val === null || val === "") return;
    const display = Array.isArray(val) ? (val as unknown[]).join(", ") : String(val);
    rows.push({ label: t(`confirm.${key}`), value: display });
  };

  add("seeker_type", profile.seeker_type);
  add("age", profile.age);
  add("gender", profile.gender);
  add("origin_state", profile.origin_state);
  add("sector", profile.sector);
  add("education", profile.education);
  add("employment_status", profile.employment_status);
  add("worker_band", profile.worker_band);
  add("aadhaar", profile.aadhaar_available ? "Yes" : "No");

  return rows;
}

export default function ConfirmPage() {
  const { t } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const reducedMotion = useReducedMotion();

  const [profile, setProfile] = useState<Record<string, unknown>>(
    (location.state as { profile?: Record<string, unknown> })?.profile ?? {}
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // If navigated here without state (e.g. direct URL), finalize from session
    if (Object.keys(profile).length === 0) {
      finalize()
        .then((res) => setProfile(res.profile))
        .catch((e) => setError(String(e)));
    }
  }, []);

  async function handleConfirm() {
    setLoading(true);
    try {
      const res = await finalize();
      setProfile(res.profile);
      // T16 will add /api/run — navigate there when ready
      navigate("/plan", { state: { profile: res.profile } });
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  const rows = profileRows(profile, t);

  return (
    <div className="min-h-dvh flex flex-col bg-background">
      <Header />

      <main className="flex-1 max-w-[600px] w-full mx-auto px-4 py-8">
        <motion.div
          initial={reducedMotion ? false : { opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="space-y-6"
        >
          <div>
            <h1 className="text-2xl font-bold text-foreground">{t("confirm.title")}</h1>
            <p className="text-sm text-muted-foreground mt-1">{t("confirm.subtitle")}</p>
          </div>

          <div className="rounded-2xl border border-border divide-y divide-border overflow-hidden">
            {rows.map(({ label, value }) => (
              <div key={label} className="flex justify-between items-center px-4 py-3 text-sm">
                <span className="text-muted-foreground">{label}</span>
                <span className="font-medium text-foreground capitalize">{value}</span>
              </div>
            ))}
          </div>

          {error && (
            <div role="alert" className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3">
              <p className="text-sm text-destructive flex-1">{error}</p>
              <button
                onClick={() => { setError(null); handleConfirm(); }}
                className="text-sm font-medium text-destructive underline underline-offset-2 shrink-0 cursor-pointer"
              >
                {t("confirm.retry")}
              </button>
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={() => navigate("/intake")}
              className="flex-1 min-h-[44px] rounded-xl border border-border text-sm font-medium hover:border-primary hover:text-primary transition-colors duration-150 cursor-pointer"
            >
              {t("confirm.edit")}
            </button>
            <button
              onClick={handleConfirm}
              disabled={loading}
              className="flex-1 min-h-[44px] rounded-xl bg-primary text-primary-foreground text-sm font-medium disabled:opacity-40 transition-opacity cursor-pointer disabled:cursor-not-allowed flex items-center justify-center gap-2"
              aria-busy={loading}
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                  <span className="sr-only">{t("confirm.submitting")}</span>
                </>
              ) : t("confirm.confirm")}
            </button>
          </div>
        </motion.div>
      </main>
    </div>
  );
}
