import { useRef, useState } from "react";
import LandingPage from "./components/LandingPage";
import WorkoutPage from "./components/WorkoutPage";
import DashboardPage from "./components/DashboardPage";
import ExerciseSelectionPage from "./components/ExerciseSelectionPage";
import CameraSetupPage from "./components/CameraSetupPage";
import ExerciseInstructionsPage from "./components/ExerciseInstructionsPage";
import { exerciseOptions } from "./components/exerciseOptions";
import type { AuthUser, Exercise } from "./services/api";
import "./styles/landing.css";

const localAthlete: AuthUser = { id: 0, email: "This device", full_name: "Athlete", picture_url: null };

export default function App() {
  const [view, setView] = useState<"landing" | "dashboard" | "exercise" | "instructions" | "camera" | "workout">("landing");
  const preparedCamera = useRef<MediaStream | null>(null);
  const [exercise, setExercise] = useState<Exercise>("Squats");
  function show(next: typeof view) { setView(next); }
  function showHistory() { window.history.replaceState({}, "", "?view=dashboard&section=history"); show("dashboard"); }
  function startSelectedWorkout(stream: MediaStream) { preparedCamera.current = stream; show("workout"); }
  const selected = exerciseOptions.find((item) => item.name === exercise) ?? exerciseOptions[0];
  if (view === "workout") {
    const stream = preparedCamera.current; preparedCamera.current = null;
    return <WorkoutPage user={localAthlete} initialExercise={exercise} preparedStream={stream ?? undefined} onBack={() => show("exercise")} onDashboard={() => show("dashboard")} onHistory={showHistory} onSignOut={() => show("landing")} />;
  }
  if (view === "dashboard") return <DashboardPage user={localAthlete} onWorkout={() => show("exercise")} onSignOut={() => show("landing")} />;
  if (view === "exercise") return <ExerciseSelectionPage user={localAthlete} onContinue={(name) => { setExercise(name); show("instructions"); }} onBack={() => show("dashboard")} onSignOut={() => show("landing")} />;
  if (view === "instructions") return <ExerciseInstructionsPage user={localAthlete} exercise={exercise} onContinue={() => show("camera")} onBack={() => show("exercise")} onDashboard={() => show("dashboard")} onSignOut={() => show("landing")} />;
  if (view === "camera") return <CameraSetupPage user={localAthlete} exercise={exercise} cameraGuidance={selected.camera} onContinue={startSelectedWorkout} onBack={() => show("instructions")} onDashboard={() => show("dashboard")} onSignOut={() => show("landing")} />;
  return <LandingPage user={null} authLoading={false} authNotice={false} onWorkout={() => show("exercise")} onDashboard={() => show("dashboard")} onSignOut={() => show("landing")} />;
}
