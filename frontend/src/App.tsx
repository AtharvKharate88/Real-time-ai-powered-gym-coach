import { useEffect, useRef, useState } from "react";
import LandingPage from "./components/LandingPage";
import WorkoutPage from "./components/WorkoutPage";
import DashboardPage from "./components/DashboardPage";
import ExerciseSelectionPage from "./components/ExerciseSelectionPage";
import CameraSetupPage from "./components/CameraSetupPage";
import ExerciseInstructionsPage from "./components/ExerciseInstructionsPage";
import { exerciseOptions } from "./components/exerciseOptions";
import { getCurrentUser, loginWithGoogle, logout, type AuthUser, type Exercise } from "./services/api";
import "./styles/landing.css";

export default function App() {
  const [view, setView] = useState<"landing" | "dashboard" | "exercise" | "instructions" | "camera" | "workout">(() => new URLSearchParams(window.location.search).get("view") === "dashboard" ? "dashboard" : "landing");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authNotice, setAuthNotice] = useState(false);
  const [error, setError] = useState("");
  const preparedCamera = useRef<MediaStream | null>(null);
  const [exercise, setExercise] = useState<Exercise>("Squats");
  useEffect(() => {
    let active = true;
    getCurrentUser().then((current) => { if (active) setUser(current); }).catch(() => { if (active) setUser(null); }).finally(() => { if (active) setAuthLoading(false); });
    const params = new URLSearchParams(window.location.search);
    if (params.get("error")) { setError("Google sign-in failed. Check OAuth settings and try again."); window.history.replaceState({}, "", import.meta.env.BASE_URL); }
    return () => { active = false; };
  }, []);
  function show(next: typeof view) { setView(next); }
  function showHistory() { window.history.replaceState({}, "", "?view=dashboard&section=history"); show("dashboard"); }
  function startSelectedWorkout(stream: MediaStream) { preparedCamera.current = stream; show("workout"); }
  function startTraining() {
    setError("");
    if (!user) { try { loginWithGoogle(); } catch (e) { setError(e instanceof Error ? e.message : "Unable to start Google sign-in."); } return; }
    show("exercise");
  }
  async function signOut() { try { await logout(); } finally { setUser(null); show("landing"); } }
  const selected = exerciseOptions.find((item) => item.name === exercise) ?? exerciseOptions[0];
  if (authLoading) return <main className="auth-check" role="status">Checking your sign-in…</main>;
  if (view !== "landing" && !user) return <LandingPage user={null} authLoading={false} authNotice onWorkout={startTraining} onDashboard={startTraining} onSignOut={() => void signOut()} />;
  if (view === "workout") {
    return <WorkoutPage user={user!} initialExercise={exercise} preparedStream={preparedCamera.current ?? undefined} onBack={() => show("exercise")} onDashboard={() => show("dashboard")} onHistory={showHistory} onSignOut={() => void signOut()} />;
  }
  if (view === "dashboard") return <DashboardPage user={user!} onWorkout={() => show("exercise")} onSignOut={() => void signOut()} />;
  if (view === "exercise") return <ExerciseSelectionPage user={user!} onContinue={(name) => { setExercise(name); show("instructions"); }} onBack={() => show("dashboard")} onSignOut={() => void signOut()} />;
  if (view === "instructions") return <ExerciseInstructionsPage user={user!} exercise={exercise} onContinue={() => show("camera")} onBack={() => show("exercise")} onDashboard={() => show("dashboard")} onSignOut={() => void signOut()} />;
  if (view === "camera") return <CameraSetupPage user={user!} exercise={exercise} cameraGuidance={selected.camera} onContinue={startSelectedWorkout} onBack={() => show("instructions")} onDashboard={() => show("dashboard")} onSignOut={() => void signOut()} />;
  return <><LandingPage user={user} authLoading={false} authNotice={authNotice} onWorkout={startTraining} onDashboard={() => user ? show("dashboard") : startTraining()} onSignOut={() => void signOut()} />{error ? <p className="workout-error" role="alert">{error}</p> : null}</>;
}
