import { useState, type MouseEvent, type SyntheticEvent } from "react";
import BackendStatus from "./BackendStatus";

const galleryImages = [
  ["i1.png", "Squat form analysis", "card-tilt-left card-float-1"],
  ["i2.png", "Deadlift posture feedback", "card-center card-float-2"],
  ["i3.png", "Overhead press alignment", "card-tilt-right card-float-3"],
  ["i4.png", "Overhead press alignment", "card-tilt-right card-float-4"],
  ["i5.png", "Overhead press alignment", "card-center card-float-5"],
  ["i6.png", "Overhead press alignment", "card-tilt-left card-float-6"],
];

function markImageMissing(event: SyntheticEvent<HTMLImageElement>) {
  event.currentTarget.parentElement?.classList.add("img-placeholder");
}

function navigateToLogin(event: MouseEvent<HTMLAnchorElement>, onWorkout: () => void) {
  event.preventDefault();
  onWorkout();
}

export default function LandingPage({ onWorkout }: { onWorkout: () => void }) {
  const [videoMissing, setVideoMissing] = useState(false);

  return (
    <>
      <div className="grid-overlay" aria-hidden="true" />
      <nav className="nav">
        <div className="nav-logo">
          <span className="logo-bracket">(</span>AI GYM COACH
          <span className="logo-bracket">)</span>
        </div>
        <div className="nav-links">
          <a href="#visuals">Gallery</a>
          <a href="#demo">Demo</a>
          <a href="#contact">Contact</a>
          <BackendStatus />
        </div>
      </nav>
      <main>
        <section className="hero" id="hero">
          <div className="hero-tag"><span className="dot" /><span>AI-POWERED · REAL-TIME · GYM COACH</span></div>
          <h1 className="hero-title"><span className="line-one">REAL-TIME</span><span className="line-two">AI GYM<br />COACH</span></h1>
          <p className="hero-sub">Your form. Analyzed. Corrected. In milliseconds.<br />Computer vision that watches every rep and tells you exactly what to fix.</p>
          <div className="hero-cta-row">
            <a href="#login" className="btn-primary" id="cta-button" onClick={(event) => navigateToLogin(event, onWorkout)}><span>Start Workout</span><span aria-hidden="true">→</span></a>
            <a href="#demo-video" className="btn-ghost">WATCH DEMO ↓</a>
          </div>
          <div className="metrics-strip">
            <div className="metric"><span className="metric-val">100<span className="unit">ms</span></span><span className="metric-label">Avg Latency</span></div>
            <div className="metric-divider" />
            <div className="metric"><span className="metric-val">5<span className="unit">+</span></span><span className="metric-label">Exercises</span></div>
            <div className="metric-divider" />
            <div className="metric"><span className="metric-val">95<span className="unit">%</span></span><span className="metric-label">Form Accuracy</span></div>
          </div>
        </section>

        <section className="visuals" id="visuals">
          <div className="section-header center-header"><span className="section-tag">// GALLERY</span><h2 className="section-title">Built for<br /><em>real athletes</em></h2></div>
          <div className="card-grid">
            {galleryImages.map(([image, alt, classes]) => (
              <div className={`img-card ${classes}`} key={image}>
                <div className="card-inner"><div className="card-img-wrap">
                  <img src={`/IMGs/${image}`} alt={alt} onError={markImageMissing} /><div className="card-scan-line" />
                </div><div className="card-corner tl" /><div className="card-corner tr" /><div className="card-corner bl" /><div className="card-corner br" /></div>
              </div>
            ))}
          </div>
        </section>

        <section className="demo" id="demo">
          <div className="section-header center-header"><span className="section-tag">// DEMO</span><h2 className="section-title">See it in<br /><em>action</em></h2><p className="section-desc">Watch the AI detect and correct form errors in real-time. No hardware required — just your phone or webcam.</p></div>
          <div className="video-wrapper" id="demo-video"><div className="video-glow" /><div className="video-container">
            <div className="video-corner tl" /><div className="video-corner tr" /><div className="video-corner bl" /><div className="video-corner br" />
            <div className="video-status"><span className="dot pulse-dot" /><span>DEMO</span></div>
            {videoMissing ? <div className="video-placeholder">DEMO VIDEO NOT AVAILABLE<span>Add frontend/public/videos/video.mp4 to enable playback.</span></div> : <video src="/videos/video.mp4" controls playsInline onError={() => setVideoMissing(true)} />}
          </div></div>
          <div className="feature-row">{["Pose Detection", "Audio Feedback", "Rep Counter", "Works in Real-time"].map((feature) => <div className="feature" key={feature}><span className="feature-icon">⬡</span><strong>{feature}</strong></div>)}</div>
        </section>

        <section className="contact" id="contact"><div className="contact-inner">
          <span className="section-tag">// LET&apos;S CONNECT</span><h2 className="contact-title">Built by a human.<br /><em>Backed by data.</em></h2><p className="contact-desc">Open to opportunities in ML engineering, computer vision, and AI product roles.</p>
          <div className="social-grid">
            <a href="https://www.linkedin.com/in/prince-khunt-linked-in/" target="_blank" rel="noopener noreferrer" className="social-btn"><span className="social-label">LinkedIn</span></a>
            <a href="https://github.com/PrinceKhunt16" target="_blank" rel="noopener noreferrer" className="social-btn"><span className="social-label">GitHub</span></a>
            <a href="https://twitter.com/prince_khunt_" target="_blank" rel="noopener noreferrer" className="social-btn"><span className="social-label">Twitter</span></a>
            <a href="mailto:princekhunt04@gmail.com" className="social-btn"><span className="social-label">Gmail</span></a>
          </div>
        </div><footer className="footer"><span>© 2026 AI GYM Trainer — Real-time AI Gym Trainer</span></footer></section>
      </main>
    </>
  );
}
