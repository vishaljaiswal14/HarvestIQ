"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { useSyncOutbox } from "@/hooks/useSyncOutbox";
import { useAuthStore } from "@/stores/authStore";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 1,
          },
        },
      }),
  );

  const initialize = useAuthStore((state) => state.initialize);
  useSyncOutbox();

  useEffect(() => {
    void initialize();
  }, [initialize]);

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
