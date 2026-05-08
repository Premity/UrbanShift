import { motion, useReducedMotion } from "framer-motion";
import { cn } from "../../lib/utils";

interface Props {
  role: "agent" | "user";
  text: string;
}

export function ChatTurn({ role, text }: Props) {
  const isAgent = role === "agent";
  const reducedMotion = useReducedMotion();

  return (
    <motion.div
      initial={reducedMotion ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className={cn("flex", isAgent ? "justify-start" : "justify-end")}
      aria-live={isAgent ? "polite" : undefined}
    >
      <div
        role={isAgent ? "status" : undefined}
        className={cn(
          "max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed",
          isAgent
            ? "bg-muted text-foreground rounded-tl-sm"
            : "bg-primary text-primary-foreground rounded-tr-sm"
        )}
      >
        {text}
      </div>
    </motion.div>
  );
}
