import { useBackendHealth } from "../hooks/useBackendHealth";

export default function BackendStatus() {
  const { status, health, error } = useBackendHealth();
  const label =
    status === "loading"
      ? "Backend connecting..."
      : status === "connected"
        ? "Backend connected"
        : "Backend disconnected";

  return (
    <div
      className={`backend-status backend-status-${status}`}
      role="status"
      aria-live="polite"
      title={error ?? health?.message}
    >
      <span className="backend-status-dot" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
