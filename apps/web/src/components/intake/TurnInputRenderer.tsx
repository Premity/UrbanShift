import { useState } from "react";
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
}: {
  label: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      aria-label={label}
      className={cn(
        "min-h-[44px] px-4 py-2 rounded-full border text-sm font-medium transition-colors duration-150 cursor-pointer",
        selected
          ? "bg-primary text-primary-foreground border-primary"
          : "bg-background text-foreground border-border hover:border-primary hover:text-primary"
      )}
    >
      {label}
    </button>
  );
}

export function TurnInputRenderer({ turn, onSubmit, disabled }: Props) {
  const { input_type, options, allow_free_text, multi_select } = turn;

  const [selected, setSelected] = useState<string[]>([]);
  const [freeText, setFreeText] = useState("");

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
  }

  const canSubmit =
    selected.length > 0 || freeText.trim().length > 0;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {(input_type === "chips" || input_type === "multi") && (
        <div className="flex flex-wrap gap-2">
          {options.map((opt) => (
            <ChipButton
              key={opt}
              label={opt}
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
