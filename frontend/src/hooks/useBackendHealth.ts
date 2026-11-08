import { useEffect, useState } from "react";
import { getHealth, type HealthResponse } from "../services/api";

export type BackendStatus = "loading" | "connected" | "disconnected";

interface BackendHealthState {
  status: BackendStatus;
  health: HealthResponse | null;
  error: string | null;
}

export function useBackendHealth(): BackendHealthState {
  const [state, setState] = useState<BackendHealthState>({
    status: "loading",
    health: null,
    error: null,
  });

  useEffect(() => {
    let active = true;

    const checkHealth = () => {
      getHealth()
        .then((health) => {
          if (active) {
            setState({ status: "connected", health, error: null });
          }
        })
        .catch((error: unknown) => {
          if (active) {
            setState({
              status: "disconnected",
              health: null,
              error: error instanceof Error ? error.message : "Backend unavailable.",
            });
          }
        });
    };

    checkHealth();
    const intervalId = window.setInterval(checkHealth, 10_000);

    return () => {
      active = false;
      window.clearInterval(intervalId);
    };
  }, []);

  return state;
}
