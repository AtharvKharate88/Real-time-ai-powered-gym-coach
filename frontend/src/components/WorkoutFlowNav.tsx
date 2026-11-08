import type { AuthUser } from "../services/api";
import AuthStatus from "./AuthStatus";

const steps = ["Choose exercise", "Review instructions", "Set up camera", "Start workout"] as const;
export type WorkoutFlowStep = 0 | 1 | 2 | 3;

export default function WorkoutFlowNav({
  user,
  step,
  onDashboard,
  onSignOut,
}: {
  user: AuthUser;
  step: WorkoutFlowStep;
  onDashboard: () => void;
  onSignOut: () => void;
}) {
  return (
    <nav className="nav flow-nav" aria-label="Workout navigation">
      <button type="button" className="nav-logo flow-brand" onClick={onDashboard} aria-label="Go to dashboard">
        <span className="logo-bracket">(</span>AI GYM COACH<span className="logo-bracket">)</span>
      </button>
      <div className="flow-progress" aria-label={`Step ${step + 1} of ${steps.length}: ${steps[step]}`}>
        <div className="flow-progress-copy"><span>STEP {step + 1} OF {steps.length}</span><strong>{steps[step]}</strong></div>
        <div className="flow-progress-track" aria-hidden="true">{steps.map((label, index) => <span key={label} className={index <= step ? "is-complete" : ""} />)}</div>
      </div>
      <div className="flow-actions">
        <button type="button" className="flow-dashboard-link" onClick={onDashboard}>Dashboard</button>
        <AuthStatus user={user} loading={false} onSignOut={onSignOut} />
      </div>
    </nav>
  );
}
