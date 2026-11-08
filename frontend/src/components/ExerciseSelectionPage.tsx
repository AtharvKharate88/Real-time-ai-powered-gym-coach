import type { AuthUser, Exercise } from "../services/api";
import ExerciseIllustration from "./ExerciseIllustration";
import WorkoutFlowNav from "./WorkoutFlowNav";
import { exerciseOptions } from "./exerciseOptions";

interface ExerciseSelectionPageProps {
  user: AuthUser;
  onContinue: (exercise: Exercise) => void;
  onBack: () => void;
  onSignOut: () => void;
}

export default function ExerciseSelectionPage({ user, onContinue, onBack, onSignOut }: ExerciseSelectionPageProps) {
  return (
    <main className="exercise-page redesigned-exercise-page">
      <WorkoutFlowNav user={user} step={0} onDashboard={onBack} onSignOut={onSignOut} />
      <section className="exercise-content library-content">
        <div className="library-heading"><span className="eyebrow">YOUR WORKOUT</span><h1>Choose your<br /><span>next move.</span></h1><p>Pick an exercise to see how to set up and what the coach will watch for.</p></div>
        <div className="exercise-library-grid">
          {exerciseOptions.map((exercise, index) => <article className="library-card" key={exercise.name}>
            <ExerciseIllustration exercise={exercise.name} />
            <div className="library-card-content">
              <div className="library-title-row"><span className="library-index">0{index + 1}</span><span className="difficulty-pill">{exercise.difficulty}</span></div>
              <h2>{exercise.name}</h2>
              <p>{exercise.description}</p>
              <div className="library-card-meta"><span>{exercise.muscles}</span><span>{exercise.equipment}</span></div>
              <button type="button" className="button button-secondary library-select" onClick={() => onContinue(exercise.name)}>View instructions <span aria-hidden="true">→</span></button>
            </div>
          </article>)}
        </div>
      </section>
    </main>
  );
}
