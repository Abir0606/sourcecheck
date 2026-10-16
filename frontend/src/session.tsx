import { createContext, useContext, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api/endpoints";
import type { Session } from "./api/types";

interface SessionContextValue {
  session: Session | undefined;
  isLoading: boolean;
  refresh: () => void;
}

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["session"], queryFn: api.session });

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["session"] });
  };

  return (
    <SessionContext.Provider value={{ session: data, isLoading, refresh }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession(): SessionContextValue {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used within SessionProvider");
  return ctx;
}
