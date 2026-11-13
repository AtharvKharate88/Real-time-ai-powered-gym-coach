import { useState } from "react";
import type { AuthUser } from "../services/api";
import AuthStatus from "./AuthStatus";
import ExerciseIllustration from "./ExerciseIllustration";
import { exerciseOptions } from "./exerciseOptions";

const features = [
  { icon: "◎", title: "See your movement", copy: "Camera based pose tracking follows your body as you exercise." },
  { icon: "↗", title: "Count each rep", copy: "Live rep and set counts keep your session on track." },
  { icon: "⌁", title: "Get form tips", copy: "Clear cues help you make small adjustments while you move." },
  { icon: "♪", title: "Hear your coach", copy: "Optional spoken tips keep feedback easy to follow during a session." },
  { icon: "◷", title: "Keep your progress", copy: "Your sessions are saved to your account so you can look back." },
];

interface LandingPageProps {
  onWorkout: () => void;
  onDashboard: () => void;
  user: AuthUser | null;
  authLoading: boolean;
  authNotice: boolean;
  onSignOut: () => void;
}

export default function LandingPage({ onWorkout, onDashboard, user, authLoading, authNotice, onSignOut }: LandingPageProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const primaryAction = user ? onDashboard : onWorkout;

  function closeMenu() {
    setMenuOpen(false);
  }

  return (
    <div className="site-shell">
      <header className="site-header">
        <a className="site-brand" href="#home" aria-label="AI Gym Coach home">
          <span className="brand-mark">A</span><span>AI Gym Coach<small>TRAIN WITH INTENTION</small></span>
        </a>
        <button className="mobile-menu-toggle" type="button" aria-expanded={menuOpen} aria-controls="site-navigation" onClick={() => setMenuOpen((open) => !open)}>
          <span>{menuOpen ? "Close" : "Menu"}</span><span className="menu-glyph" aria-hidden="true">{menuOpen ? "×" : "☰"}</span>
        </button>
        <nav id="site-navigation" className={`site-navigation${menuOpen ? " is-open" : ""}`} aria-label="Main navigation">
          <a href="#features" onClick={closeMenu}>Features</a>
          <a href="#exercises" onClick={closeMenu}>Exercises</a>
          <a href="#about" onClick={closeMenu}>About</a>
          {user ? <div className="site-nav-meta"><AuthStatus user={user} loading={authLoading} onSignOut={onSignOut} /></div> : null}
          <button className="button button-small button-primary" type="button" disabled={authLoading} onClick={() => { closeMenu(); primaryAction(); }}>
            {authLoading ? "Checking account" : user ? "Open dashboard" : "Sign in with Google"}
          </button>
        </nav>
      </header>

      <main>
        <section className="hero-section" id="home">
          <div className="hero-copy">
            <div className="eyebrow"><span className="status-dot" />YOUR PERSONAL AI TRAINING PARTNER</div>
            <h1>Train smarter.<br /><span>Move better.</span><br />Get stronger.</h1>
            <p>Your personal AI gym coach. Track every rep, improve your form, and get real-time coaching with your camera.</p>
            <div className="hero-actions">
              <button className="button button-primary" type="button" disabled={authLoading} onClick={primaryAction}>
                {authLoading ? "Checking account" : user ? "Open dashboard" : "Start training"}<span aria-hidden="true">→</span>
              </button>
              <a className="button button-secondary" href="#features">Explore features</a>
            </div>
            {authNotice ? <p className="inline-alert" role="alert">Sign in with Google before starting a workout.</p> : null}
            <div className="hero-proof"><span className="proof-icon">✓</span><span>Works with your webcam</span><span className="proof-divider" /><span>5 supported exercises</span></div>
          </div>
          <div className="hero-art-wrap">
            <div className="hero-art-glow" aria-hidden="true" />
            <div className="hero-art-frame"><ExerciseIllustration exercise="Squats" className="hero-illustration" />
              <div className="hero-art-caption"><span className="live-indicator" /><div><strong>Live form guidance</strong><span>Move at your own pace</span></div><span className="caption-signal" aria-hidden="true">•••</span></div>
            </div>
            <div className="floating-note note-top"><span className="note-icon">◎</span><span><strong>Body tracking</strong><small>Camera based</small></span></div>
            <div className="floating-note note-bottom"><span className="note-icon note-check">✓</span><span><strong>Coach is ready</strong><small>Start when you are</small></span></div>
          </div>
        </section>

        <section className="feature-section content-section" id="features">
          <div className="section-intro"><span className="eyebrow">A LITTLE MORE FOCUS, EVERY REP</span><h2>Training that pays<br />attention.</h2><p>Useful guidance while you train, with your progress saved for next time.</p></div>
          <div className="feature-grid">{features.map((feature, index) => <article className="feature-card" key={feature.title}>
            <div className="feature-card-top"><span className="feature-icon">{feature.icon}</span><span className="feature-index">0{index + 1}</span></div>
            <h3>{feature.title}</h3><p>{feature.copy}</p>
          </article>)}</div>
        </section>

        <section className="exercise-showcase content-section" id="exercises">
          <div className="section-heading-row"><div><span className="eyebrow">YOUR MOVEMENT LIBRARY</span><h2>Five moves.<br /><span>One focused coach.</span></h2></div><p>Choose a movement, get your camera set up, and the coach will take it from there.</p></div>
          <div className="landing-exercise-grid">{exerciseOptions.map((exercise) => <article className="landing-exercise-card" key={exercise.name}>
            <ExerciseIllustration exercise={exercise.name} />
            <div className="landing-exercise-info"><div><h3>{exercise.name}</h3><span>{exercise.difficulty}</span></div><p>{exercise.description}</p><small>{exercise.muscles}</small></div>
          </article>)}</div>
          <div className="showcase-action"><button className="button button-primary" type="button" disabled={authLoading} onClick={primaryAction}>{user ? "Go to your dashboard" : "Choose your first workout"}<span aria-hidden="true">→</span></button></div>
        </section>

        <section className="about-section content-section" id="about">
          <div className="about-mark" aria-hidden="true">A</div>
          <div><span className="eyebrow">BUILT AROUND YOUR MOVEMENT</span><h2>A more thoughtful<br />way to train.</h2><p>AI Gym Coach uses your camera to follow supported exercises, count repetitions, and offer simple form cues. It keeps your workout history so you can see your effort add up.</p>
            <button type="button" className="text-button" onClick={primaryAction} disabled={authLoading}>{user ? "Open your dashboard" : "Get started"}<span aria-hidden="true">→</span></button>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <a className="site-brand" href="#home"><span className="brand-mark">A</span><span>AI Gym Coach<small>TRAIN WITH INTENTION</small></span></a>
        <p>Personal training feedback, powered by computer vision.</p>
        <div className="footer-links"><a href="https://github.com/AtharvKharate88" target="_blank" rel="noopener noreferrer">GitHub</a><a href="https://www.linkedin.com/in/atharv-kharate-8ab34032b?utm_source=share_via&amp;utm_content=profile&amp;utm_medium=member_android" target="_blank" rel="noopener noreferrer">LinkedIn</a><a href="mailto:atharvkharate7799@gmail.com">Email</a></div>
        <small>© {new Date().getFullYear()} AI Gym Coach</small>
      </footer>
    </div>
  );
}
