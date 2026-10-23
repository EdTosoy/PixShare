"use client";

import { ClerkProvider, useAuth } from "@clerk/nextjs";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createContext, useContext, useState } from "react";

const configured = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);
const SessionContext = createContext({
  configured,
  isLoaded: true,
  isSignedIn: false,
  userId: null as string | null,
  getToken: async (): Promise<string | null> => null,
});

export function useSession() {
  return useContext(SessionContext);
}

function QueryProvider({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: true },
        },
      }),
  );
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

function ClerkSession({ children }: { children: React.ReactNode }) {
  const { isLoaded, isSignedIn, userId, getToken } = useAuth();
  return (
    <SessionContext.Provider
      value={{
        configured,
        isLoaded,
        isSignedIn: Boolean(isSignedIn),
        userId: userId ?? null,
        getToken,
      }}
    >
      {/* A fresh cache on account changes keeps private galleries isolated. */}
      <QueryProvider key={userId ?? "visitor"}>{children}</QueryProvider>
    </SessionContext.Provider>
  );
}

export function Providers({ children }: { children: React.ReactNode }) {
  if (!configured) return <QueryProvider>{children}</QueryProvider>;
  return (
    <ClerkProvider
      signInUrl="/sign-in"
      signUpUrl="/sign-up"
      signInFallbackRedirectUrl="/me"
      signUpFallbackRedirectUrl="/me"
    >
      <ClerkSession>{children}</ClerkSession>
    </ClerkProvider>
  );
}
