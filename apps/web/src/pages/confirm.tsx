import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useForm, Controller } from "react-hook-form";
import { motion, useReducedMotion } from "framer-motion";
import { Loader2, CheckCircle2 } from "lucide-react";
import { Header } from "../components/shared/Header";
import { finalize, saveProfile, type ProfilePayload } from "../lib/intake";

// ── Helpers ──────────────────────────────────────────────

function SelectField({
  id,
  label,
  options,
  value,
  onChange,
  disabled,
  error,
}: {
  id: string;
  label: string;
  options: { value: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
  error?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className={`text-xs font-medium uppercase tracking-wide ${error ? "text-destructive" : "text-muted-foreground"}`}>
        {label}
      </label>
      <select
        id={id}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className={`w-full min-h-[44px] rounded-xl border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 disabled:opacity-50 ${
          error ? "border-destructive focus:ring-destructive/40" : "border-border focus:ring-primary/40"
        }`}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}

function NumberField({
  id,
  label,
  value,
  onChange,
  min,
  max,
  disabled,
  error,
}: {
  id: string;
  label: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  disabled?: boolean;
  error?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className={`text-xs font-medium uppercase tracking-wide ${error ? "text-destructive" : "text-muted-foreground"}`}>
        {label}
      </label>
      <input
        id={id}
        type="number"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        disabled={disabled}
        className={`w-full min-h-[44px] rounded-xl border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 disabled:opacity-50 ${
          error ? "border-destructive focus:ring-destructive/40" : "border-border focus:ring-primary/40"
        }`}
      />
    </div>
  );
}

function TextField({
  id,
  label,
  value,
  onChange,
  placeholder,
  disabled,
  error,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  disabled?: boolean;
  error?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className={`text-xs font-medium uppercase tracking-wide ${error ? "text-destructive" : "text-muted-foreground"}`}>
        {label}
      </label>
      <input
        id={id}
        type="text"
        value={value ?? ""}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className={`w-full min-h-[44px] rounded-xl border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 disabled:opacity-50 capitalize ${
          error ? "border-destructive focus:ring-destructive/40" : "border-border focus:ring-primary/40"
        }`}
      />
    </div>
  );
}

// Multi-value comma-separated helper
function MultiTextField({
  id,
  label,
  hint,
  value,
  onChange,
  placeholder,
  disabled,
  error,
}: {
  id: string;
  label: string;
  hint: string;
  value: string[];
  onChange: (v: string[]) => void;
  placeholder?: string;
  disabled?: boolean;
  error?: boolean;
}) {
  const raw = Array.isArray(value) ? value.join(", ") : "";
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className={`text-xs font-medium uppercase tracking-wide ${error ? "text-destructive" : "text-muted-foreground"}`}>
        {label}
        <span className="ml-1 normal-case font-normal text-muted-foreground/70">({hint})</span>
      </label>
      <input
        id={id}
        type="text"
        defaultValue={raw}
        placeholder={placeholder}
        onBlur={(e) =>
          onChange(
            e.target.value
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean)
          )
        }
        disabled={disabled}
        className={`w-full min-h-[44px] rounded-xl border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 disabled:opacity-50 capitalize ${
          error ? "border-destructive focus:ring-destructive/40" : "border-border focus:ring-primary/40"
        }`}
      />
    </div>
  );
}

// ── Language code ↔ full-name map ───────────────────────

const LANG_CODE_TO_NAME: Record<string, string> = {
  en: "English",
  hi: "Hindi",
  kn: "Kannada",
  ta: "Tamil",
  te: "Telugu",
  ml: "Malayalam",
  mr: "Marathi",
  gu: "Gujarati",
  pa: "Punjabi",
  bn: "Bengali",
  or: "Odia",
  as: "Assamese",
  ur: "Urdu",
  sa: "Sanskrit",
  sd: "Sindhi",
  ne: "Nepali",
  kok: "Konkani",
  mai: "Maithili",
  bho: "Bhojpuri",
};

// reverse: lowercase full-name → ISO code (for submit)
const LANG_NAME_TO_CODE: Record<string, string> = Object.fromEntries(
  Object.entries(LANG_CODE_TO_NAME).map(([code, name]) => [name.toLowerCase(), code])
);

function codeToLangName(code: string): string {
  return LANG_CODE_TO_NAME[code.toLowerCase()] ?? code;
}

function langNameToCode(name: string): string {
  return LANG_NAME_TO_CODE[name.toLowerCase()] ?? name.toLowerCase();
}

// ── Helpers: map raw profile JSON → typed ProfilePayload ─

function rawToPayload(raw: Record<string, unknown>): ProfilePayload {
  return {
    seeker_type: (raw.seeker_type as ProfilePayload["seeker_type"]) ?? "both",
    name: (raw.name as string) ?? undefined,
    age: Number(raw.age ?? 0),
    gender: (raw.gender as ProfilePayload["gender"]) ?? "prefer_not",
    origin_state: (raw.origin_state as string) ?? "",
    current_city: "Bengaluru",
    native_lang: codeToLangName((raw.native_lang as string) ?? ""),
    languages_spoken: ((raw.languages_spoken as string[]) ?? []).map(codeToLangName),
    migrant_status: (raw.migrant_status as ProfilePayload["migrant_status"]) ?? "just_moved",
    aadhaar_available: Boolean(raw.aadhaar_available ?? false),
    sector: (raw.sector as string) ?? undefined,
    skills: (raw.skills as string[]) ?? [],
    education: (raw.education as ProfilePayload["education"]) ?? "none",
    years_experience: Number(raw.years_experience ?? 0),
    employment_status: (raw.employment_status as ProfilePayload["employment_status"]) ?? "unemployed",
    income_range_inr: (raw.income_range_inr as [number, number]) ?? null,
    worker_band: Number(raw.worker_band ?? 1),
    budget_inr: raw.budget_inr != null ? Number(raw.budget_inr) : null,
    preferred_areas: (raw.preferred_areas as string[]) ?? [],
    occupancy_pref: (raw.occupancy_pref as ProfilePayload["occupancy_pref"]) ?? null,
    move_in_window_days: (raw.move_in_window_days != null && Number(raw.move_in_window_days) > 0)
      ? Number(raw.move_in_window_days)
      : null,
  };
}

// ── Page ──────────────────────────────────────────────────

export default function ConfirmPage() {
  const { t } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const reducedMotion = useReducedMotion();

  const rawProfile = (location.state as { profile?: Record<string, unknown> })?.profile ?? {};

  const {
    control,
    handleSubmit,
    reset,
    watch,
    formState: { isSubmitting, errors },
  } = useForm<ProfilePayload>({
    defaultValues: rawToPayload(rawProfile),
  });

  const seekerType = watch("seeker_type");

  // If navigated without state (direct URL), finalize from session
  useEffect(() => {
    if (Object.keys(rawProfile).length === 0) {
      finalize()
        .then((res) => reset(rawToPayload(res.profile as Record<string, unknown>)))
        .catch(console.error);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onSubmit(data: ProfilePayload) {
    // Convert full language names back to ISO codes before saving
    const payload: ProfilePayload = {
      ...data,
      native_lang: langNameToCode(data.native_lang),
      languages_spoken: data.languages_spoken.map(langNameToCode),
    };
    await saveProfile(payload);
    navigate("/processing", { state: { profile: payload } });
  }

  const sectionClass = "space-y-4 rounded-2xl border border-border p-4";
  const sectionTitle = "text-sm font-semibold text-foreground mb-3";

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
          {/* Heading */}
          <div>
            <h1 className="text-2xl font-bold text-foreground">{t("confirm.title")}</h1>
            <p className="text-sm text-muted-foreground mt-1">{t("confirm.subtitle")}</p>
          </div>

          <form id="confirm-form" onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">

            {/* ── Section: About You ── */}
            <section aria-labelledby="section-about" className={sectionClass}>
              <h2 id="section-about" className={sectionTitle}>{t("confirm.section_about")}</h2>
              <div className="grid grid-cols-2 gap-3">

                <Controller
                  name="seeker_type"
                  control={control}
                  rules={{ required: true }}
                  render={({ field, fieldState }) => (
                    <SelectField
                      id="confirm-seeker_type"
                      label={t("confirm.seeker_type")}
                      value={field.value}
                      onChange={field.onChange}
                      error={!!fieldState.error}
                      options={[
                        { value: "job", label: t("intake.seekerType.job") },
                        { value: "housing", label: t("intake.seekerType.housing") },
                        { value: "both", label: t("intake.seekerType.both") },
                      ]}
                    />
                  )}
                />

                <Controller
                  name="age"
                  control={control}
                  rules={{ min: 1, max: 120 }}
                  render={({ field, fieldState }) => (
                    <NumberField
                      id="confirm-age"
                      label={t("confirm.age")}
                      value={field.value}
                      onChange={field.onChange}
                      min={1}
                      max={120}
                      error={!!fieldState.error}
                    />
                  )}
                />

                <Controller
                  name="gender"
                  control={control}
                  render={({ field }) => (
                    <SelectField
                      id="confirm-gender"
                      label={t("confirm.gender")}
                      value={field.value}
                      onChange={field.onChange}
                      options={[
                        { value: "male", label: t("intake.options.male") },
                        { value: "female", label: t("intake.options.female") },
                        { value: "other", label: t("intake.options.other") },
                        { value: "prefer_not", label: t("intake.options.prefer_not") },
                      ]}
                    />
                  )}
                />

                <Controller
                  name="origin_state"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      id="confirm-origin_state"
                      label={t("confirm.origin_state")}
                      value={field.value}
                      onChange={field.onChange}
                      placeholder="e.g. Bihar, UP"
                    />
                  )}
                />

                <Controller
                  name="native_lang"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      id="confirm-native_lang"
                      label={t("confirm.native_lang")}
                      value={field.value}
                      onChange={field.onChange}
                      placeholder="e.g. hi, kn"
                    />
                  )}
                />

                <Controller
                  name="migrant_status"
                  control={control}
                  render={({ field }) => (
                    <SelectField
                      id="confirm-migrant_status"
                      label={t("confirm.migrant_status")}
                      value={field.value}
                      onChange={field.onChange}
                      options={[
                        { value: "just_moved", label: t("intake.options.just_moved") },
                        { value: "planning", label: t("intake.options.planning") },
                        { value: "long_term", label: t("confirm.long_term") },
                      ]}
                    />
                  )}
                />
              </div>

              <Controller
                name="languages_spoken"
                control={control}
                render={({ field }) => (
                  <MultiTextField
                    id="confirm-languages_spoken"
                    label={t("confirm.languages_spoken")}
                    hint={t("confirm.comma_separated", "comma-separated")}
                    value={field.value}
                    onChange={field.onChange}
                    placeholder="hi, en, kn"
                  />
                )}
              />

              <div className="flex items-center gap-3 pt-1">
                <Controller
                  name="aadhaar_available"
                  control={control}
                  render={({ field }) => (
                    <>
                      <button
                        id="confirm-aadhaar"
                        type="button"
                        role="switch"
                        aria-checked={field.value}
                        onClick={() => field.onChange(!field.value)}
                        className={`relative w-11 h-6 rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-primary/40 ${
                          field.value ? "bg-primary" : "bg-muted-foreground/30"
                        }`}
                      >
                        <span
                          className={`absolute top-1 left-1 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200 ${
                            field.value ? "translate-x-5" : "translate-x-0"
                          }`}
                        />
                      </button>
                      <label htmlFor="confirm-aadhaar" className="text-sm text-foreground cursor-pointer" onClick={() => field.onChange(!field.value)}>
                        {t("confirm.aadhaar")}
                      </label>
                    </>
                  )}
                />
              </div>
            </section>

            {/* ── Section: Work ── */}
            <section aria-labelledby="section-work" className={sectionClass}>
              <h2 id="section-work" className={sectionTitle}>{t("confirm.section_work")}</h2>
              <div className="grid grid-cols-2 gap-3">

                <Controller
                  name="sector"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      id="confirm-sector"
                      label={t("confirm.sector")}
                      value={field.value ?? ""}
                      onChange={field.onChange}
                      placeholder="driving, bpo…"
                    />
                  )}
                />

                <Controller
                  name="education"
                  control={control}
                  render={({ field }) => (
                    <SelectField
                      id="confirm-education"
                      label={t("confirm.education")}
                      value={field.value}
                      onChange={field.onChange}
                      options={[
                        { value: "none", label: t("intake.options.none") },
                        { value: "primary", label: t("intake.options.primary") },
                        { value: "class10", label: t("intake.options.class10") },
                        { value: "class12", label: t("intake.options.class12") },
                        { value: "diploma", label: t("intake.options.diploma") },
                        { value: "grad", label: t("intake.options.grad") },
                        { value: "postgrad", label: t("intake.options.postgrad") },
                      ]}
                    />
                  )}
                />

                <Controller
                  name="years_experience"
                  control={control}
                  render={({ field }) => (
                    <NumberField
                      id="confirm-years_experience"
                      label={t("confirm.years_experience")}
                      value={field.value}
                      onChange={field.onChange}
                      min={0}
                      max={50}
                    />
                  )}
                />

                <Controller
                  name="employment_status"
                  control={control}
                  render={({ field }) => (
                    <SelectField
                      id="confirm-employment_status"
                      label={t("confirm.employment_status")}
                      value={field.value}
                      onChange={field.onChange}
                      options={[
                        { value: "unemployed", label: t("intake.options.unemployed") },
                        { value: "employed", label: t("intake.options.employed") },
                        { value: "underemployed", label: t("intake.options.underemployed") },
                        { value: "student", label: t("intake.options.student") },
                      ]}
                    />
                  )}
                />

                {/* worker_band is auto-derived by the backend — not user-editable */}
              </div>

              <Controller
                name="skills"
                control={control}
                render={({ field }) => (
                  <MultiTextField
                    id="confirm-skills"
                    label={t("confirm.skills")}
                    hint={t("confirm.comma_separated", "comma-separated")}
                    value={field.value}
                    onChange={field.onChange}
                    placeholder="driving, customer service…"
                  />
                )}
              />
            </section>

            {/* ── Section: Housing (conditional) ── */}
            {seekerType !== "job" && (
              <section aria-labelledby="section-housing" className={sectionClass}>
                <h2 id="section-housing" className={sectionTitle}>{t("confirm.section_housing")}</h2>
                <div className="grid grid-cols-2 gap-3">

                  <Controller
                    name="budget_inr"
                    control={control}
                    render={({ field }) => (
                      <NumberField
                        id="confirm-budget_inr"
                        label={t("confirm.budget_inr")}
                        value={field.value ?? 0}
                        onChange={(v) => field.onChange(v || null)}
                        min={0}
                      />
                    )}
                  />

                  <Controller
                    name="occupancy_pref"
                    control={control}
                    render={({ field }) => (
                      <SelectField
                        id="confirm-occupancy_pref"
                        label={t("confirm.occupancy_pref")}
                        value={field.value ?? "any"}
                        onChange={(v) => field.onChange(v === "any" ? null : v)}
                        options={[
                          { value: "any", label: t("confirm.any") },
                          { value: "single", label: t("confirm.single") },
                          { value: "shared", label: t("confirm.shared") },
                          { value: "dorm", label: t("confirm.dorm") },
                        ]}
                      />
                    )}
                  />

                  <Controller
                    name="move_in_window_days"
                    control={control}
                    render={({ field }) => (
                      <NumberField
                        id="confirm-move_in_window_days"
                        label={t("confirm.move_in_window_days")}
                        value={field.value ?? 0}
                        onChange={(v) => field.onChange(v || null)}
                        min={0}
                        max={365}
                      />
                    )}
                  />
                </div>

                <Controller
                  name="preferred_areas"
                  control={control}
                  render={({ field }) => (
                    <MultiTextField
                      id="confirm-preferred_areas"
                      label={t("confirm.preferred_areas")}
                      hint={t("confirm.comma_separated", "comma-separated")}
                      value={field.value}
                      onChange={field.onChange}
                      placeholder="Koramangala, HSR, Whitefield"
                    />
                  )}
                />
              </section>
            )}

            {/* ── Error ── */}
            {Object.keys(errors).length > 0 && (
              <div role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3">
                <p className="text-sm text-destructive">{t("confirm.validation_error")}</p>
              </div>
            )}

            {/* ── Actions ── */}
            <div className="pt-1">
              <button
                type="submit"
                form="confirm-form"
                disabled={isSubmitting}
                className="w-full min-h-[52px] rounded-xl bg-primary text-primary-foreground text-sm font-semibold disabled:opacity-40 transition-opacity cursor-pointer disabled:cursor-not-allowed flex items-center justify-center gap-2"
                aria-busy={isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    <span>{t("confirm.submitting")}</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                    <span>{t("confirm.confirm")}</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </motion.div>
      </main>
    </div>
  );
}
