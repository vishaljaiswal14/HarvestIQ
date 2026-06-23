"use client";

import Image from "next/image";
import Link from "next/link";

import { cn } from "@/lib/utils";

export const BRAND = {
  icon: "/branding/logo-icon.webp",
  wordmark: "/branding/logo-wordmark.png",
  cover: "/branding/brand-cover.png",
  subtitle: "Agricultural Intelligence Platform",
} as const;

type HarvestIQLogoProps = {
  variant?: "icon" | "wordmark" | "full" | "stacked";
  size?: "xs" | "sm" | "md" | "lg" | "xl";
  subtitle?: boolean;
  href?: string | null;
  className?: string;
  priority?: boolean;
  subtitleTheme?: "light" | "dark";
};

const ICON_SIZES = { xs: 28, sm: 36, md: 44, lg: 56, xl: 80 };
const WORDMARK_HEIGHT = { xs: 24, sm: 32, md: 40, lg: 48, xl: 64 };

export function HarvestIQLogo({
  variant = "full",
  size = "md",
  href = "/",
  className,
  priority = false,
}: HarvestIQLogoProps) {
  const iconPx = ICON_SIZES[size];
  const wordmarkH = WORDMARK_HEIGHT[size];

  const content = (
    <div className={cn("flex items-center", className)}>
      {variant === "icon" ? (
        <Image
          src={BRAND.icon}
          alt="HarvestIQ"
          width={iconPx}
          height={iconPx}
          priority={priority}
          className="shrink-0 rounded-full object-cover shadow-sm ring-1 ring-emerald-100"
        />
      ) : variant === "stacked" ? (
        <div className="flex flex-col items-center gap-3">
          <Image
            src={BRAND.icon}
            alt="HarvestIQ"
            width={iconPx}
            height={iconPx}
            priority={priority}
            className="shrink-0 rounded-full object-cover shadow-sm ring-2 ring-white/20"
          />
          <span className={cn(
            "font-bold tracking-tight text-white",
            size === "xl" ? "text-3xl" : "text-xl"
          )}>
            HarvestIQ
          </span>
        </div>
      ) : (
        <Image
          src={BRAND.wordmark}
          alt="HarvestIQ"
          width={Math.round(wordmarkH * 4.2)}
          height={wordmarkH}
          priority={priority}
          className="h-auto w-auto max-w-[140px] object-contain sm:max-w-[180px]"
          style={{ height: wordmarkH, width: "auto" }}
        />
      )}
    </div>
  );
  if (href) {
    return (
      <Link href={href} className="shrink-0 transition-opacity hover:opacity-90">
        {content}
      </Link>
    );
  }

  return content;
}
