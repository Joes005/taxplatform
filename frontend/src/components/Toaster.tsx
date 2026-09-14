import { CheckCircle2, XCircle, Info, X } from "lucide-react";

import { useToast } from "@/hooks/useToast";
import { cn } from "@/lib/utils";

export function Toaster() {
  const { toasts, dismiss } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-[100] flex w-full max-w-sm flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={cn(
            "flex items-start gap-3 rounded-lg border bg-white p-4 shadow-lg",
            t.variant === "destructive" && "border-destructive/30",
            t.variant === "success" && "border-success/30",
            (!t.variant || t.variant === "default") && "border-border"
          )}
        >
          {t.variant === "destructive" && <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />}
          {t.variant === "success" && <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success" />}
          {(!t.variant || t.variant === "default") && (
            <Info className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
          )}
          <div className="flex-1 text-sm">
            <p className="font-medium text-foreground">{t.title}</p>
            {t.description && <p className="mt-0.5 text-muted-foreground">{t.description}</p>}
          </div>
          <button
            onClick={() => dismiss(t.id)}
            className="text-muted-foreground hover:text-foreground"
            aria-label="Dismiss"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  );
}
