"use client";

import type { ReactNode } from "react";
import Image from "next/image";

import { BRAND, HarvestIQLogo } from "@/components/branding/HarvestIQLogo";
import { PwaStatusBar } from "@/components/PwaStatusBar";

type AuthBrandLayoutProps = {
  children: ReactNode;
  title: string;
  description: string;
};

export function AuthBrandLayout({ children, title, description }: AuthBrandLayoutProps) {
  return (
    <div className="dashboard-shell flex min-h-full flex-1 flex-col">
      <div className="relative overflow-hidden border-b border-emerald-100 bg-gradient-to-br from-emerald-950 via-emerald-900 to-teal-900 px-4 py-8 sm:py-12">
        <div className="hero-pattern absolute inset-0 opacity-10" />
        <div className="relative mx-auto flex max-w-md flex-col items-center text-center">
          <HarvestIQLogo
            variant="stacked"
            size="xl"
            href={null}
            priority
          />
          <p className="mt-4 max-w-xs text-sm leading-relaxed text-emerald-100/80">
            AI-powered crop yield risk forecasting and field intelligence.
          </p>
        </div>
      </div>

      <main className="mx-auto flex w-full max-w-md flex-1 flex-col px-4 py-8">
        <PwaStatusBar />
        <div className="mb-4 text-center sm:text-left">
          <h1 className="text-xl font-bold text-slate-900">{title}</h1>
          <p className="mt-1 text-sm text-slate-600">{description}</p>
        </div>
        {children}
      </main>
    </div>
  );
}
