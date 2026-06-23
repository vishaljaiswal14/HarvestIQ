import * as React from "react";

import { cn } from "@/lib/utils";
import {
  alertSeverity,
  SEVERITY_STYLES,
  type SeverityLevel,
} from "@/lib/dashboard-theme";

type BadgeProps = React.HTMLAttributes<HTMLSpanElement> & {
  severity?: SeverityLevel;
  variant?: "solid" | "outline" | "dot";
};

export function Badge({
  className,
  severity = "neutral",
  variant = "solid",
  children,
  ...props
}: BadgeProps) {
  const styles = SEVERITY_STYLES[severity];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold tracking-wide uppercase",
        variant === "solid" && [styles.bg, styles.text],
        variant === "outline" && ["border bg-white", styles.border, styles.text],
        variant === "dot" && ["border bg-white", styles.border, styles.text],
        className,
      )}
      {...props}
    >
      {variant === "dot" && (
        <span
          className="h-1.5 w-1.5 rounded-full"
          style={{ backgroundColor: styles.accent }}
        />
      )}
      {children}
    </span>
  );
}

export function AlertSeverityBadge({ severity }: { severity: string }) {
  return <Badge severity={alertSeverity(severity)}>{severity}</Badge>;
}
