import { AlertCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

type EmptyStateProps = {
  message: string;
  title?: string;
  icon?: LucideIcon;
  action?: {
    label: string;
    onClick: () => void;
  };
  actionLink?: {
    label: string;
    href: string;
  };
};

export function EmptyState({
  message,
  title,
  icon: Icon = AlertCircle,
  action,
  actionLink,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center text-center p-6 rounded-xl border border-dashed border-slate-200 bg-slate-50/30 w-full min-h-[120px]">
      <div className="rounded-full bg-slate-50 p-2.5 text-slate-400 border border-slate-100 mb-2">
        <Icon className="h-5 w-5" />
      </div>
      {title && <p className="text-xs font-bold text-slate-700 mb-0.5">{title}</p>}
      <p className="text-xs text-slate-500 max-w-xs leading-relaxed">{message}</p>
      
      {action && (
        <Button
          onClick={action.onClick}
          size="sm"
          variant="outline"
          className="mt-3 h-8 text-[11px] rounded-lg border-slate-200 hover:border-emerald-300 hover:text-emerald-700"
        >
          {action.label}
        </Button>
      )}

      {actionLink && (
        <Button
          asChild
          size="sm"
          variant="outline"
          className="mt-3 h-8 text-[11px] rounded-lg border-slate-200 hover:border-emerald-300 hover:text-emerald-700"
        >
          <Link href={actionLink.href}>{actionLink.label}</Link>
        </Button>
      )}
    </div>
  );
}
