import { useEffect, useRef, useState } from "react";
import LandingPage from "./components/LandingPage";
import WorkoutPage from "./components/WorkoutPage";
import DashboardPage from "./components/DashboardPage";
import ExerciseSelectionPage from "./components/ExerciseSelectionPage";
import CameraSetupPage from "./components/CameraSetupPage";
import ExerciseInstructionsPage from "./components/ExerciseInstructionsPage";
import { exerciseOptions } from "./components/exerciseOptions";
import {
  getCurrentUser,
  loginWithGoogle,
  logout,
  type AuthUser,
  type Exercise,
} from "./services/api";
import "./styles/landing.css";

export default function App() {
  const [view, setView] = useState<"landing" | "dashboard" | "exercise" | "instructions" | "camera" | "workout">(() => {
    const requestedView = new URLSearchParams(window.location.search).get("view");
    return requestedView === "workout" || requestedView === "dashboard" || requestedView === "exercise" || requestedView === "instructions" || requestedView === "camera"
      ? requestedView
      : "landing";
  });
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authNotice, setAuthNotice] = useState(false);
  const preparedCamera = useRef<MediaStream | null>(null);

  useEffect(() => {
    let active = true;
    getCurrentUser()
      .then((currentUser) => {
        if (active) setUser(currentUser);
      })
      .catch(() => {
        if (active) setUser(null);
      })
      .finally(() => {
        if (active) setAuthLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (authLoading || user || view === "landing") return;
    window.history.replaceState({}, "", "/");
    setView("landing");
    setAuthNotice(true);
  }, [authLoading, user, view]);

  function showDashboard() {
    window.history.pushState({}, "", "?view=dashboard");
    setView("dashboard");
    setAuthNotice(false);
  }

  function showWorkoutHistory() {
    window.history.pushState({}, "", "?view=dashboard&section=history");
    setView("dashboard");
  }

  function showExerciseSelection() {
    window.history.pushState({}, "", "?view=exercise");
    setView("exercise");
    setAuthNotice(false);
  }

  function showExerciseInstructions(exercise: Exercise) {
    window.history.pushState({}, "", `?view=instructions&exercise=${encodeURIComponent(exercise)}`);
    setView("instructions");
    setAuthNotice(false);
  }

  function prepareWorkoutCamera(exercise: Exercise) {
    window.history.pushState({}, "", `?view=camera&exercise=${encodeURIComponent(exercise)}`);
    setView("camera");
    setAuthNotice(false);
  }

  function startSelectedWorkout(stream: MediaStream) {
    preparedCamera.current = stream;
    const exercise = new URLSearchParams(window.location.search).get("exercise") ?? "Squats";
    window.history.replaceState({}, "", `?view=workout&exercise=${encodeURIComponent(exercise)}`);
    setView("workout");
    setAuthNotice(false);
  }

  function showLanding() {
    window.history.pushState({}, "", "/");
    setView("landing");
  }

  function startWorkout() {
    if (authLoading) return;
    if (!user) {
      loginWithGoogle();
      return;
    }
    showExerciseSelection();
  }

  async function signOut() {
    await logout();
    setUser(null);
    setAuthNotice(false);
    showLanding();
  }

  if (view !== "landing" && authLoading) {
    return (
      <main className="auth-check" role="status">
        Checking your sign-in…
      </main>
    );
  }

  if (view === "workout" && user) {
    const requestedExercise = new URLSearchParams(window.location.search).get("exercise");
    const exercise = exerciseOptions.find((option) => option.name === requestedExercise)?.name;
    const cameraStream = preparedCamera.current;
    preparedCamera.current = null;
    return <WorkoutPage user={user} initialExercise={exercise} preparedStream={cameraStream ?? undefined} onBack={showExerciseSelection} onDashboard={showDashboard} onHistory={showWorkoutHistory} onSignOut={() => void signOut()} />;
  }
  if (view === "dashboard" && user) {
    return <DashboardPage user={user} onWorkout={showExerciseSelection} onSignOut={() => void signOut()} />;
  }
  if (view === "exercise" && user) {
    return <ExerciseSelectionPage user={user} onContinue={showExerciseInstructions} onBack={showDashboard} onSignOut={() => void signOut()} />;
  }
  if (view === "instructions" && user) {
    const requestedExercise = new URLSearchParams(window.location.search).get("exercise");
    const option = exerciseOptions.find((item) => item.name === requestedExercise) ?? exerciseOptions[0];
    return <ExerciseInstructionsPage user={user} exercise={option.name} onContinue={() => prepareWorkoutCamera(option.name)} onBack={showExerciseSelection} onDashboard={showDashboard} onSignOut={() => void signOut()} />;
  }
  if (view === "camera" && user) {
    const requestedExercise = new URLSearchParams(window.location.search).get("exercise");
    const option = exerciseOptions.find((item) => item.name === requestedExercise) ?? exerciseOptions[0];
    return <CameraSetupPage user={user} cameraGuidance={option.camera} onContinue={startSelectedWorkout} onBack={() => showExerciseInstructions(option.name)} onDashboard={showDashboard} onSignOut={() => void signOut()} />;
  }

  return (
    <LandingPage
      onWorkout={startWorkout}
      onDashboard={showDashboard}
      user={user}
      authLoading={authLoading}
      authNotice={authNotice}
      onSignOut={() => void signOut()}
    />
  );
}
