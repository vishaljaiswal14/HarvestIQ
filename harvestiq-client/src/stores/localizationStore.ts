import { create } from "zustand";
import { persist } from "zustand/middleware";
import { api } from "@/lib/api";
import { readCachedSnapshot } from "@/lib/db";
import { en, type TranslationKey } from "@/locales/en";
import { hi } from "@/locales/hi";

export const DEFAULT_DICTS: Record<string, Record<string, string>> = {
  en,
  hi,
};

type LocalizationState = {
  preferredLang: string;
  dictionary: Record<string, string>;
  isLoading: boolean;
  setLanguage: (lang: string) => Promise<void>;
  loadTranslations: (lang: string) => Promise<void>;
};

export const useLocalizationStore = create<LocalizationState>()(
  persist(
    (set, get) => ({
      preferredLang: "hi",
      dictionary: {},
      isLoading: false,

      setLanguage: async (lang) => {
        set({ preferredLang: lang });
        await get().loadTranslations(lang);
      },

      loadTranslations: async (lang) => {
        set({ isLoading: true, preferredLang: lang });

        try {
          // Attempt API fetch (this also writes to IndexedDB on success)
          const res = await api.getLocalization(lang);
          if (res && res.labels) {
            set({ dictionary: res.labels });
          } else {
            set({ dictionary: {} });
          }
        } catch (error) {
          console.warn("[LocalizationStore] API load failed, loading from IndexedDB:", error);
          try {
            // Retrieve from IndexedDB offline cache
            const cached = await readCachedSnapshot<any>("localization", lang);
            if (cached && cached.labels) {
              set({ dictionary: cached.labels });
            } else {
              set({ dictionary: {} });
            }
          } catch (dbErr) {
            console.error("[LocalizationStore] IndexedDB read failed:", dbErr);
            set({ dictionary: {} });
          }
        } finally {
          set({ isLoading: false });
        }
      },
    }),
    {
      name: "localization-storage",
      partialize: (state) => ({
        preferredLang: state.preferredLang,
      }),
    }
  )
);

if (typeof window !== 'undefined') { (window as any).useLocalizationStore = useLocalizationStore; }

/**
 * Synchronous global translation helper function.
 * Looks up translation by key from the active Zustand localization dictionary.
 * Falls back to active default dictionary, then to the provided fallback value,
 * and finally to the key itself if no match is found.
 */
export function t(key: TranslationKey | string, fallback?: string): string {
  const state = useLocalizationStore.getState();
  const dict = state.dictionary;
  const lang = state.preferredLang;
  const defaults = DEFAULT_DICTS[lang] || DEFAULT_DICTS.en;
  return dict[key] ?? (defaults as any)[key] ?? fallback ?? key;
}

export function useTranslation() {
  const dictionary = useLocalizationStore((state) => state.dictionary);
  const preferredLang = useLocalizationStore((state) => state.preferredLang);

  const tFunc = (key: TranslationKey | string, fallback?: string): string => {
    const defaults = DEFAULT_DICTS[preferredLang] || DEFAULT_DICTS.en;
    return dictionary[key] ?? (defaults as any)[key] ?? fallback ?? key;
  };

  return { t: tFunc, preferredLang };
}
