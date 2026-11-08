import type { AuthUser, Exercise } from "../services/api";
import ExerciseIllustration from "./ExerciseIllustration";
import WorkoutFlowNav from "./WorkoutFlowNav";
import { exerciseOptions } from "./exerciseOptions";

const coachChecks: Record<Exercise, string[]> = {
  "Squats": ["Squat low enough for a full repetition", "Keep your chest lifted"],
  "Push-ups": ["Keep your body in a straight line", "Lower under control"],
  "Biceps Curls (Dumbbell)": ["Keep your elbows close to your sides", "Avoid rocking your body"],
  "Shoulder Press": ["Reach overhead with control", "Keep your lower back steady"],
  "Lunges": ["Keep your stance balanced", "Lower and rise with control"],
};

export default function ExerciseInstructionsPage({
  user,
  exercise,
  onContinue,
  onBack,
  onDashboard,
  onSignOut,
}: {
  user: AuthUser;
  exercise: Exercise;
  onContinue: () => void;
  onBack: () => void;
  onDashboard: () => void;
  onSignOut: () => void;
}) {
  const details = exerciseOptions.find((option) => option.name === exercise) ?? exerciseOptions[0];

  return (
    <main className="exercise-page redesigned-exercise-page">
      <WorkoutFlowNav user={user} step={1} onDashboard={onDashboard} onSignOut={onSignOut} />
      <section className="instructions-content">
        <button type="button" className="text-button back-link" onClick={onBack}>← All exercises</button>
        <div className="instructions-layout">
          <div className="instructions-art-column"><ExerciseIllustration exercise={exercise} className="instructions-art" /><div className="exercise-quick-facts"><div><span>Equipment</span><strong>{details.equipment}</strong></div><div><span>Works</span><strong>{details.muscles}</strong></div><div><span>Level</span><strong>{details.difficulty}</strong></div></div></div>
          <div className="instructions-copy"><span className="eyebrow">BEFORE YOU BEGIN</span><h1>{exercise}</h1><p className="instructions-description">{details.description}</p>
            <section><h2>Set up your camera</h2><p>{details.camera}</p></section>
            <section><h2>How to do it</h2><ol>{details.instructions.map((instruction) => <li key={instruction}>{instruction}</li>)}</ol></section>
            <section className="coach-checks"><h2>What your coach will watch for</h2><ul>{coachChecks[exercise].map((tip) => <li key={tip}>{tip}</li>)}</ul></section>
            <button type="button" className="button button-primary instruction-cta" onClick={onContinue}>Set up camera <span aria-hidden="true">→</span></button>
          </div>
        </div>
      </section>
    </main>
  );
}
