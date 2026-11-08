export interface HealthResponse {
  status: string;
  message: string;
}

export type Exercise =
  | "Squats"
  | "Push-ups"
  | "Biceps Curls (Dumbbell)"
  | "Shoulder Press"
  | "Lunges";

export interface WorkoutSession {
  session_id: string;
  exercise: Exercise;
  target_sets: number;
  reps_per_set: number;
  status: "ready" | "running" | "paused" | "stopped";
}

export interface WorkoutMetrics {
  session_id: string;
  status: WorkoutSession["status"];
  exercise: Exercise;
  reps: number;
  sets_completed: number;
  current_set_reps: number;
  workout_completed: boolean;
  elapsed_seconds: number;
  metrics: Record<string, number | string | boolean>;
}

export interface VoiceResponse {
  text: string;
  audio_base64: string | null;
}

export interface HistoryEntry {
  exercise_name: string;
  reps: number;
  sets: number;
  time: number;
  created_at: string;
}

interface SessionActionResponse {
  session_id: string;
  status: "running" | "paused" | "stopped";
}

interface WebRTCAnswer {
  sdp: string;
  type: "answer";
}

export class ApiError extends Error {
  readonly statusCode: number;

  constructor(message: string, statusCode: number) {
    super(message);
    this.name = "ApiError";
    this.statusCode = statusCode;
  }
}

const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
const apiBaseUrl = configuredApiBaseUrl?.replace(/\/$/, "") ?? "";

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  if (!apiBaseUrl) {
    throw new ApiError(
      "VITE_API_BASE_URL is not configured. Restart Vite after creating frontend/.env.",
      0,
    );
  }

  let response: Response;

  try {
    response = await fetch(`${apiBaseUrl}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });
  } catch {
    throw new ApiError("Unable to reach the backend.", 0);
  }

  if (!response.ok) {
    throw new ApiError(`Backend returned HTTP ${response.status}.`, response.status);
  }

  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError("Backend returned an invalid response.", response.status);
  }
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
}

export function createWorkoutSession(
  exercise: Exercise,
  targetSets: number,
  repsPerSet: number,
): Promise<WorkoutSession> {
  return request<WorkoutSession>("/api/workouts/sessions", {
    method: "POST",
    body: JSON.stringify({
      exercise,
      target_sets: targetSets,
      reps_per_set: repsPerSet,
    }),
  });
}

export function updateWorkoutStatus(
  sessionId: string,
  action: "start" | "pause" | "stop",
): Promise<SessionActionResponse> {
  return request<SessionActionResponse>(
    `/api/workouts/sessions/${sessionId}/${action}`,
    { method: "POST" },
  );
}

export function getWorkoutMetrics(sessionId: string): Promise<WorkoutMetrics> {
  return request<WorkoutMetrics>(
    `/api/workouts/sessions/${sessionId}/metrics`,
  );
}

export function getVoice(sessionId: string): Promise<VoiceResponse | null> {
  return request<VoiceResponse | null>(
    `/api/workouts/sessions/${sessionId}/voice`,
  );
}

export function getWorkoutHistory(): Promise<HistoryEntry[]> {
  return request<HistoryEntry[]>("/api/workouts/history");
}

export function submitWebRTCOffer(
  sessionId: string,
  offer: RTCSessionDescriptionInit,
): Promise<WebRTCAnswer> {
  return request<WebRTCAnswer>(`/api/webrtc/offer?session_id=${sessionId}`, {
    method: "POST",
    body: JSON.stringify(offer),
  });
}
