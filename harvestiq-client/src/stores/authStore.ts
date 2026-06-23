import { create } from "zustand";
import { persist } from "zustand/middleware";

import { api, type FarmProfile, type UserProfile } from "@/lib/api";
import { clearAccessToken, setAccessToken } from "@/lib/auth";

type AuthState = {
  user: UserProfile | null;
  farm: FarmProfile | null;
  lastSyncAt: string | null;
  isLoading: boolean;
  isInitialized: boolean;
  hasHydrated: boolean;
  error: string | null;
  initialize: () => Promise<void>;
  login: (phone: string, password: string) => Promise<void>;
  register: (
    name: string,
    phone: string,
    password: string,
    preferredLang?: string,
  ) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  setFarm: (farm: FarmProfile | null) => void;
  setHasHydrated: (state: boolean) => void;
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      farm: null,
      lastSyncAt: null,
      isLoading: false,
      isInitialized: false,
      hasHydrated: false,
      error: null,

      setHasHydrated: (state) => set({ hasHydrated: state }),

      initialize: async () => {
        if (get().isInitialized) return;
        set({ isLoading: true, error: null });

        const isOnline =
          typeof navigator !== "undefined" ? navigator.onLine : true;

        try {
          const refreshResponse = await fetch("/api/v1/auth/refresh", {
            method: "POST",
            credentials: "include",
          });

          if (refreshResponse.ok) {
            const data = (await refreshResponse.json()) as {
              access_token: string;
            };
            setAccessToken(data.access_token);
            const user = await api.getMe();
            set({ user, isInitialized: true });

            if (user.onboarding_completed) {
              try {
                const farm = await api.getFarmProfile();
                set({ farm, lastSyncAt: new Date().toISOString() });
              } catch {
                set({ farm: null });
              }
            }
          } else if (
            refreshResponse.status === 401 ||
            refreshResponse.status === 403
          ) {
            // Explicit server rejection — only clear session when online
            if (isOnline) {
              clearAccessToken();
              set({ user: null, farm: null, isInitialized: true });
            } else {
              // Offline — keep persisted session
              set({ isInitialized: true });
            }
          } else {
            // 5xx or unexpected — treat as network failure, preserve offline state
            set({ isInitialized: true });
          }
        } catch {
          // Network error (offline). Keep existing user/farm from persist to
          // allow offline PWA usage. Do NOT clear or redirect.
          set({ isInitialized: true });
        } finally {
          set({ isLoading: false });
        }
      },

      login: async (phone, password) => {
        set({ isLoading: true, error: null });
        try {
          const tokenData = await api.login({ phone, password });
          setAccessToken(tokenData.access_token);
          const user = await api.getMe();

          let farm: FarmProfile | null = null;
          if (user.onboarding_completed) {
            try {
              farm = await api.getFarmProfile();
            } catch {
              farm = null;
            }
          }

          set({
            user,
            farm,
            lastSyncAt: new Date().toISOString(),
            isInitialized: true,
          });
        } catch (error) {
          clearAccessToken();
          set({
            user: null,
            farm: null,
            error: error instanceof Error ? error.message : "Login failed",
          });
          throw error;
        } finally {
          set({ isLoading: false });
        }
      },

      register: async (name, phone, password, preferredLang = "hi") => {
        set({ isLoading: true, error: null });
        try {
          await api.register({ name, phone, password, preferred_lang: preferredLang });
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : "Registration failed",
          });
          throw error;
        } finally {
          set({ isLoading: false });
        }
      },

      logout: async () => {
        set({ isLoading: true });
        try {
          await api.logout();
        } catch {
          // Best-effort logout even if server call fails
        } finally {
          clearAccessToken();
          set({
            user: null,
            farm: null,
            lastSyncAt: null,
            isLoading: false,
            isInitialized: true,
            error: null,
          });
        }
      },

      refreshUser: async () => {
        const user = await api.getMe();
        set({ user });
        if (user.onboarding_completed) {
          const farm = await api.getFarmProfile();
          set({ farm, lastSyncAt: new Date().toISOString() });
        }
      },

      setFarm: (farm) => set({ farm }),
    }),
    {
      name: "harvestiq-auth",
      partialize: (state) => ({
        user: state.user,
        farm: state.farm,
        lastSyncAt: state.lastSyncAt,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    },
  ),
);
