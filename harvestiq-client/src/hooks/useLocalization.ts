"use client";

import { useTranslation, t as globalT } from "@/stores/localizationStore";

export function useLocalization(lang: string) {
  const { preferredLang } = useTranslation();
  return {
    data: {
      lang: preferredLang,
      labels: {},
    },
    isLoading: false,
  };
}

export function t(labels: Record<string, string> | undefined, key: string, fallback: string) {
  return globalT(key, fallback);
}
