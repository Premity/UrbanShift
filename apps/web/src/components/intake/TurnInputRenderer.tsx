import { useState } from "react";
import { useTranslation } from "react-i18next";
import { cn } from "../../lib/utils";
import type { Turn } from "../../lib/intake";

interface Props {
  turn: Turn;
  onSubmit: (value: unknown) => void;
  disabled?: boolean;
}

function ChipButton({
  label,
  selected,
  onClick,
  disabled: chipDisabled,
}: {
  label: string;
  selected: boolean;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={chipDisabled}
      aria-pressed={selected}
      aria-label={label}
      className={cn(
        "min-h-[44px] px-4 py-2 rounded-full border text-sm font-medium transition-colors duration-150",
        chipDisabled
          ? "opacity-35 cursor-not-allowed bg-background text-muted-foreground border-border"
          : selected
          ? "bg-primary text-primary-foreground border-primary cursor-pointer"
          : "bg-background text-foreground border-border hover:border-primary hover:text-primary cursor-pointer"
      )}
    >
      {label}
    </button>
  );
}

export function TurnInputRenderer({ turn, onSubmit, disabled }: Props) {
  const { t } = useTranslation();
  const { input_type, options, allow_free_text, multi_select } = turn;

  const [selected, setSelected] = useState<string[]>([]);
  const [freeText, setFreeText] = useState("");

  const [originState, setOriginState] = useState("");
  const [migrantStatus, setMigrantStatus] = useState("just_moved");

  const [age, setAge] = useState("");
  const [gender, setGender] = useState("");

  const [sector, setSector] = useState("");
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);

  const [nativeLang, setNativeLang] = useState("");
  const [otherLangs, setOtherLangs] = useState<string[]>([]);

  const [education, setEducation] = useState("");
  const [yearsExp, setYearsExp] = useState("");

  const [employmentStatus, setEmploymentStatus] = useState("");
  const [incomeMin, setIncomeMin] = useState("");
  const [incomeMax, setIncomeMax] = useState("");

  const [budget, setBudget] = useState("");
  const [preferredAreas, setPreferredAreas] = useState<string[]>([]);
  const [occupancyPref, setOccupancyPref] = useState("");

  function toggleChip(opt: string) {
    if (multi_select || input_type === "multi") {
      setSelected((prev) =>
        prev.includes(opt) ? prev.filter((v) => v !== opt) : [...prev, opt]
      );
    } else {
      setSelected([opt]);
    }
  }

  function buildValue(): unknown {
    if (turn.field === "native_lang") {
      return { native_lang: nativeLang, languages_spoken: otherLangs };
    }
    if (turn.field === "origin_state") {
      return { origin_state: originState, migrant_status: migrantStatus };
    }
    if (turn.field === "age") {
      return { age: age ? parseInt(age, 10) : 0, gender: gender };
    }
    if (turn.field === "sector") {
      return { sector: sector, skills: selectedSkills };
    }
    if (turn.field === "education") {
      return { education: education, years_experience: yearsExp ? parseInt(yearsExp, 10) : 0 };
    }
    if (turn.field === "employment_status") {
      const income: [number, number] | null =
        incomeMin && incomeMax
          ? [parseInt(incomeMin, 10), parseInt(incomeMax, 10)]
          : null;
      return { employment_status: employmentStatus, income_range_inr: income };
    }
    if (turn.field === "budget_inr") {
      return {
        budget_inr: budget ? parseInt(budget, 10) : null,
        preferred_areas: preferredAreas,
        occupancy_pref: occupancyPref || null,
      };
    }
    if (input_type === "multi") return selected;
    if (input_type === "chips") {
      if (allow_free_text && freeText && selected.length === 0) return freeText;
      return selected[0] ?? freeText;
    }
    if (input_type === "text") return freeText;
    return selected[0] ?? freeText;
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const value = buildValue();
    if (!value && value !== 0) return;
    onSubmit(value);
    setSelected([]);
    setFreeText("");
    setOriginState("");
    setMigrantStatus("just_moved");
    setAge("");
    setGender("");
    setSector("");
    setSelectedSkills([]);
    setNativeLang("");
    setOtherLangs([]);
    setEducation("");
    setYearsExp("");
    setEmploymentStatus("");
    setBudget("");
    setPreferredAreas([]);
    setOccupancyPref("");
    setIncomeMin("");
    setIncomeMax("");
  }

  const canSubmit =
    turn.field === "native_lang"
      ? nativeLang !== ""
      : turn.field === "origin_state"
      ? originState !== ""
      : turn.field === "age"
      ? age !== "" && gender !== ""
      : turn.field === "sector"
      ? sector !== "" && selectedSkills.length > 0
      : turn.field === "education"
      ? education !== "" && yearsExp !== ""
      : turn.field === "employment_status"
      ? employmentStatus !== ""
      : turn.field === "budget_inr"
      ? budget !== ""
      : selected.length > 0 || freeText.trim().length > 0;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {turn.field === "native_lang" ? (
        <div className="space-y-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Native Language
            </label>
            <div className="flex flex-wrap gap-2">
              {options.map((opt) => (
                <ChipButton
                  key={opt}
                  label={t(`language.${opt}`, t(`intake.options.${opt}`, opt))}
                  selected={nativeLang === opt}
                  onClick={() => {
                    if (disabled) return;
                    setNativeLang(opt);
                    // Remove from otherLangs if it was selected there
                    setOtherLangs((prev) => prev.filter((v) => v !== opt));
                  }}
                />
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Other Languages You Speak
            </label>
            <div className="flex flex-wrap gap-2">
              {options.map((opt) => (
                <ChipButton
                  key={opt}
                  label={t(`language.${opt}`, t(`intake.options.${opt}`, opt))}
                  selected={otherLangs.includes(opt)}
                  disabled={opt === nativeLang}
                  onClick={() => {
                    if (disabled || opt === nativeLang) return;
                    setOtherLangs((prev) =>
                      prev.includes(opt) ? prev.filter((v) => v !== opt) : [...prev, opt]
                    );
                  }}
                />
              ))}
            </div>
          </div>
        </div>
      ) : turn.field === "origin_state" ? (
        <div className="space-y-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="state-select" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              {t("confirm.origin_state", "Origin State")}
            </label>
            <select
              id="state-select"
              value={originState}
              onChange={(e) => setOriginState(e.target.value)}
              disabled={disabled}
              className="w-full min-h-[44px] px-3 py-2 rounded-xl border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring cursor-pointer"
            >
              <option value="">Select your state...</option>
              {options.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Current Situation
            </label>
            <div className="flex flex-wrap gap-2">
              {["just_moved", "planning", "been_here"].map((opt) => (
                <ChipButton
                  key={opt}
                  label={t(`intake.options.${opt}`, opt)}
                  selected={migrantStatus === opt}
                  onClick={() => !disabled && setMigrantStatus(opt)}
                />
              ))}
            </div>
          </div>
        </div>
      ) : turn.field === "age" ? (
        <div className="space-y-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="age-input" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              {t("confirm.age", "Age")}
            </label>
            <input
              id="age-input"
              type="number"
              min="1"
              max="120"
              value={age}
              onChange={(e) => setAge(e.target.value)}
              disabled={disabled}
              placeholder="Enter your age…"
              className="w-full min-h-[44px] px-4 py-2 rounded-xl border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring text-sm"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              {t("confirm.gender", "Gender")}
            </label>
            <div className="flex flex-wrap gap-2">
              {options.map((opt) => (
                <ChipButton
                  key={opt}
                  label={t(`intake.options.${opt}`, opt)}
                  selected={gender === opt}
                  onClick={() => !disabled && setGender(opt)}
                />
              ))}
            </div>
          </div>
        </div>
      ) : turn.field === "sector" ? (
        <div className="space-y-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              {t("confirm.sector", "Sector of Interest")}
            </label>
            <div className="flex flex-wrap gap-2">
              {options.map((opt) => (
                <ChipButton
                  key={opt}
                  label={t(`intake.options.${opt}`, opt)}
                  selected={sector === opt}
                  onClick={() => !disabled && setSector(opt)}
                />
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Your Skills (Select multiple)
            </label>
            <div className="flex flex-wrap gap-2 max-h-[160px] overflow-y-auto pr-1">
              {[
                "driving_license",
                "two_wheeler",
                "english",
                "computer_basics",
                "customer_service",
                "sales",
                "cooking",
                "cleaning",
                "electrical",
                "plumbing",
                "masonry",
                "security"
              ].map((opt) => (
                <ChipButton
                  key={opt}
                  label={t(`intake.options.${opt}`, opt)}
                  selected={selectedSkills.includes(opt)}
                  onClick={() => {
                    if (disabled) return;
                    setSelectedSkills((prev) =>
                      prev.includes(opt) ? prev.filter((v) => v !== opt) : [...prev, opt]
                    );
                  }}
                />
              ))}
            </div>
          </div>
        </div>
      ) : turn.field === "education" ? (
        <div className="space-y-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              {t("confirm.education", "Highest Education")}
            </label>
            <div className="flex flex-wrap gap-2">
              {options.map((opt) => (
                <ChipButton
                  key={opt}
                  label={t(`intake.options.${opt}`, opt)}
                  selected={education === opt}
                  onClick={() => !disabled && setEducation(opt)}
                />
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="exp-input" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Years of Work Experience
            </label>
            <input
              id="exp-input"
              type="number"
              min="0"
              max="60"
              value={yearsExp}
              onChange={(e) => setYearsExp(e.target.value)}
              disabled={disabled}
              placeholder="e.g. 3"
              className="w-full min-h-[44px] px-4 py-2 rounded-xl border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring text-sm"
            />
          </div>
        </div>
      ) : turn.field === "employment_status" ? (
        <div className="space-y-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              {t("confirm.employment_status", "Current Employment")}
            </label>
            <div className="flex flex-wrap gap-2">
              {options.map((opt) => (
                <ChipButton
                  key={opt}
                  label={t(`intake.options.${opt}`, opt)}
                  selected={employmentStatus === opt}
                  onClick={() => !disabled && setEmploymentStatus(opt)}
                />
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Monthly Income Range (₹) — Optional
            </label>
            <div className="flex gap-3">
              <input
                id="income-min"
                type="number"
                min="0"
                value={incomeMin}
                onChange={(e) => setIncomeMin(e.target.value)}
                disabled={disabled}
                placeholder="Min e.g. 8000"
                className="flex-1 min-h-[44px] px-4 py-2 rounded-xl border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring text-sm"
              />
              <span className="self-center text-muted-foreground text-sm">–</span>
              <input
                id="income-max"
                type="number"
                min="0"
                value={incomeMax}
                onChange={(e) => setIncomeMax(e.target.value)}
                disabled={disabled}
                placeholder="Max e.g. 20000"
                className="flex-1 min-h-[44px] px-4 py-2 rounded-xl border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring text-sm"
              />
            </div>
          </div>
        </div>
      ) : turn.field === "budget_inr" ? (
        <div className="space-y-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="budget-input" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Monthly Budget (₹)
            </label>
            <input
              id="budget-input"
              type="number"
              min="0"
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              disabled={disabled}
              placeholder="e.g. 6000"
              className="w-full min-h-[44px] px-4 py-2 rounded-xl border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring text-sm"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Preferred Areas — Optional
            </label>
            <div className="flex flex-wrap gap-2">
              {[
                "Koramangala", "HSR Layout", "Whitefield", "Electronic City",
                "BTM Layout", "Marathahalli", "Indiranagar", "Hebbal",
                "Jayanagar", "Yelahanka"
              ].map((area) => (
                <ChipButton
                  key={area}
                  label={area}
                  selected={preferredAreas.includes(area)}
                  onClick={() => {
                    if (disabled) return;
                    setPreferredAreas((prev) =>
                      prev.includes(area) ? prev.filter((a) => a !== area) : [...prev, area]
                    );
                  }}
                />
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Room Preference — Optional
            </label>
            <div className="flex flex-wrap gap-2">
              {["single", "shared", "dorm", "any"].map((opt) => (
                <ChipButton
                  key={opt}
                  label={t(`confirm.${opt}`, opt)}
                  selected={occupancyPref === opt}
                  onClick={() => !disabled && setOccupancyPref(occupancyPref === opt ? "" : opt)}
                />
              ))}
            </div>
          </div>
        </div>
      ) : (
        <>
          {(input_type === "chips" || input_type === "multi") && (
            <div className="flex flex-wrap gap-2">
              {options.map((opt) => (
                <ChipButton
                  key={opt}
                  label={t(`language.${opt}`, t(`intake.options.${opt}`, opt))}
                  selected={selected.includes(opt)}
                  onClick={() => !disabled && toggleChip(opt)}
                />
              ))}
            </div>
          )}

          {(input_type === "text" || allow_free_text) && (
            <div className="flex flex-col gap-1">
              <label htmlFor="turn-input" className="text-xs font-medium text-muted-foreground">
                {input_type === "text" ? "Your answer" : "Or type your own"}
              </label>
              <input
                id="turn-input"
                type="text"
                value={freeText}
                onChange={(e) => setFreeText(e.target.value)}
                disabled={disabled}
                placeholder={input_type === "text" ? "Type your answer…" : "Or type here…"}
                className="w-full min-h-[44px] px-4 py-2 rounded-lg border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring text-sm"
              />
            </div>
          )}
        </>
      )}

      <button
        type="submit"
        disabled={disabled || !canSubmit}
        className="w-full min-h-[44px] bg-primary text-primary-foreground rounded-lg font-medium text-sm transition-opacity disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
      >
        Next →
      </button>
    </form>
  );
}
