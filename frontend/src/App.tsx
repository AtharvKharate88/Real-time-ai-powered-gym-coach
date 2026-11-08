import { useState } from "react";
import LandingPage from "./components/LandingPage";
import WorkoutPage from "./components/WorkoutPage";
import "./styles/landing.css";

export default function App() {
  const [workout, setWorkout] = useState(
    new URLSearchParams(window.location.search).get("view") === "workout",
  );

  function showWorkout() {
    window.history.pushState({}, "", "?view=workout");
    setWorkout(true);
  }

  function showLanding() {
    window.history.pushState({}, "", "/");
    setWorkout(false);
  }

  return workout ? <WorkoutPage onBack={showLanding} /> : <LandingPage onWorkout={showWorkout} />;
}
