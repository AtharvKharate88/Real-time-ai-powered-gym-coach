import { useEffect, useMemo, useState, type FormEvent } from "react";
import type { AuthUser, Exercise, HistoryEntry } from "../services/api";
import { addLocalManualWorkout, readLocalWorkoutHistory } from "../services/api";

type DashboardSection = "dashboard" | "history" | "profile" | "settings";
const exerciseNames: Exercise[] = ["Squats", "Push-ups", "Biceps Curls (Dumbbell)", "Shoulder Press", "Lunges"];

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Date unavailable" : date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function localDayKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function readVoicePreference(): boolean {
  try { return window.localStorage.getItem("ai_gym_voice_coaching") !== "false"; }
  catch { return true; }
}

export default function DashboardPage({ user, onWorkout, onSignOut }: { user: AuthUser; onWorkout: () => void; onSignOut: () => void }) {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [activeSection, setActiveSection] = useState<DashboardSection>(() => new URLSearchParams(window.location.search).get("section") === "history" ? "history" : "dashboard");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [calendarMonth, setCalendarMonth] = useState(() => new Date(new Date().getFullYear(), new Date().getMonth(), 1));
  const [selectedDay, setSelectedDay] = useState(() => new Date());
  const [showManualForm, setShowManualForm] = useState(false);
  const [manualSaving, setManualSaving] = useState(false);
  const [manualError, setManualError] = useState("");
  const [expandedWorkout, setExpandedWorkout] = useState<string | null>(null);
  const [voiceEnabled, setVoiceEnabled] = useState(readVoicePreference);

  useEffect(() => {
    let active = true;
    if (active) { setHistory(readLocalWorkoutHistory()); setLoading(false); }
    return () => { active = false; };
  }, []);

  useEffect(() => {
    try { window.localStorage.setItem("ai_gym_voice_coaching", String(voiceEnabled)); }
    catch { /* Preferences remain available for this page even if storage is disabled. */ }
  }, [voiceEnabled]);

  const totalReps = history.reduce((total, entry) => total + entry.reps, 0);
  const totalSets = history.reduce((total, entry) => total + entry.sets, 0);
  const sortedHistory = useMemo(() => [...history].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at)), [history]);
  const recent = sortedHistory.slice(0, 4);
  const weekDays = Array.from({ length: 7 }, (_, index) => {
    const date = new Date();
    date.setHours(0, 0, 0, 0);
    date.setDate(date.getDate() - (6 - index));
    const count = history.filter((entry) => {
      const created = new Date(entry.created_at);
      return !Number.isNaN(created.getTime()) && localDayKey(created) === localDayKey(date);
    }).length;
    return { date, label: date.toLocaleDateString(undefined, { weekday: "short" }), count };
  });
  const weeklyWorkouts = weekDays.reduce((total, day) => total + day.count, 0);
  const maxDailyWorkouts = Math.max(1, ...weekDays.map((day) => day.count));
  const calendarCells = useMemo(() => {
    const firstWeekday = new Date(calendarMonth.getFullYear(), calendarMonth.getMonth(), 1).getDay();
    const days = new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() + 1, 0).getDate();
    return [...Array.from({ length: firstWeekday }, () => null), ...Array.from({ length: days }, (_, index) => new Date(calendarMonth.getFullYear(), calendarMonth.getMonth(), index + 1))];
  }, [calendarMonth]);
  const workoutsByDay = useMemo(() => {
    const grouped = new Map<string, HistoryEntry[]>();
    for (const entry of history) {
      const date = new Date(entry.created_at);
      if (!Number.isNaN(date.getTime())) grouped.set(localDayKey(date), [...(grouped.get(localDayKey(date)) ?? []), entry]);
    }
    return grouped;
  }, [history]);
  const selectedEntries = workoutsByDay.get(localDayKey(selectedDay)) ?? [];
  const exerciseTotals = exerciseNames.map((name) => ({ name, reps: history.filter((entry) => entry.exercise_name === name).reduce((sum, entry) => sum + entry.reps, 0), sessions: history.filter((entry) => entry.exercise_name === name).length })).filter((item) => item.sessions > 0).sort((a, b) => b.reps - a.reps);
  const sectionNames: Record<DashboardSection, string> = { dashboard: "Overview", history: "Workout history", profile: "Your profile", settings: "Settings" };
  const firstName = user.full_name?.trim().split(/\s+/)[0] || "there";

  async function submitManualWorkout(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const date = new Date(`${String(form.get("date"))}T12:00:00`);
    setManualSaving(true);
    setManualError("");
    try {
      const saved = addLocalManualWorkout({
        exercise_name: String(form.get("exercise")) as Exercise,
        reps: Number(form.get("reps")),
        sets: Number(form.get("sets")),
        time: Number(form.get("minutes")) * 60,
        created_at: date.toISOString(),
      });
      setHistory((entries) => [saved, ...entries]);
      setSelectedDay(date);
      setCalendarMonth(new Date(date.getFullYear(), date.getMonth(), 1));
      setShowManualForm(false);
    } catch {
      setManualError("We couldn’t save that workout on this device.");
    } finally {
      setManualSaving(false);
    }
  }

  function setSection(section: DashboardSection) {
    setActiveSection(section);
    setMobileNavOpen(false);
  }

  function renderHistory(entries: HistoryEntry[]) {
    return entries.map((entry, index) => {
      const key = `${entry.created_at}-${entry.exercise_name}-${index}`;
      const expanded = expandedWorkout === key;
      return <article className="history-entry-card" key={key}>
        <div className="history-entry-summary"><span className="history-entry-icon">{entry.exercise_name.slice(0, 1)}</span><div className="history-entry-main"><strong>{entry.exercise_name}</strong><span>{formatDate(entry.created_at)}</span></div><div className="history-entry-number"><strong>{entry.reps}</strong><span>reps</span></div><div className="history-entry-number"><strong>{entry.sets}</strong><span>sets</span></div><div className="history-entry-number"><strong>{Math.max(0, Math.round(entry.time / 60))}</strong><span>min</span></div><button className="history-detail-toggle" type="button" aria-expanded={expanded} onClick={() => setExpandedWorkout(expanded ? null : key)}>{expanded ? "Hide details" : "Details"}</button></div>
        {entry.form_score != null ? <div className="history-score-line">Estimated form score <strong>{entry.form_score}/100</strong></div> : null}
        {expanded ? <div className="history-set-details"><strong>Rep breakdown by set target</strong>{entry.set_breakdown?.length ? <><p>Calculated from total reps and configured reps per set.</p><ol>{entry.set_breakdown.map((reps, setIndex) => <li key={setIndex}>Set {setIndex + 1}<span>{reps} reps{setIndex >= entry.sets ? " · in progress" : ""}</span></li>)}</ol></> : <p>Per-set counts were not recorded for this session.</p>}</div> : null}
      </article>;
    });
  }

  const navItems: { id: DashboardSection | "start"; label: string; icon: string }[] = [
    { id: "dashboard", label: "Dashboard", icon: "▦" },
    { id: "start", label: "Start workout", icon: "＋" },
    { id: "history", label: "Workout history", icon: "◷" },
    { id: "profile", label: "Profile", icon: "◎" },
    { id: "settings", label: "Settings", icon: "⚙" },
  ];

  return (
    <main className="dashboard-shell">
      {mobileNavOpen ? <button className="sidebar-scrim" aria-label="Close navigation" onClick={() => setMobileNavOpen(false)} /> : null}
      <aside className={`app-sidebar${mobileNavOpen ? " is-open" : ""}`}>
        <a href="/?view=dashboard" className="site-brand sidebar-brand" aria-label="AI Gym Coach dashboard"><span className="brand-mark">A</span><span>AI Gym Coach<small>TRAIN WITH INTENTION</small></span></a>
        <span className="sidebar-label">WORKSPACE</span>
        <nav className="sidebar-nav" aria-label="Dashboard sections">
          {navItems.map((item) => item.id === "start" ? <button className="sidebar-item sidebar-start" type="button" key={item.id} onClick={onWorkout}><span>{item.icon}</span>{item.label}</button> : <button className={`sidebar-item${activeSection === item.id ? " is-active" : ""}`} type="button" key={item.id} aria-current={activeSection === item.id ? "page" : undefined} onClick={() => setSection(item.id as DashboardSection)}><span>{item.icon}</span>{item.label}</button>)}
        </nav>
        <div className="sidebar-account"><span className="profile-avatar">{firstName.slice(0, 1).toUpperCase()}</span><div><strong>{user.full_name || "Athlete"}</strong><small>{user.email}</small></div><button type="button" aria-label="Sign out" title="Sign out" onClick={onSignOut}>↗</button></div>
      </aside>

      <section className="dashboard-main">
        <header className="dashboard-topbar"><button className="dashboard-menu-toggle" type="button" aria-expanded={mobileNavOpen} onClick={() => setMobileNavOpen((open) => !open)}><span aria-hidden="true">☰</span><span>Menu</span></button><span className="dashboard-breadcrumb">Workspace <span>/</span> {sectionNames[activeSection]}</span><button type="button" className="button button-primary button-small topbar-start" onClick={onWorkout}>＋ Start workout</button></header>
        <div className="dashboard-content redesigned-dashboard-content">
          {activeSection === "dashboard" ? <>
            <div className="dashboard-heading redesigned-dashboard-heading"><div><span className="eyebrow">YOUR TRAINING SPACE</span><h1>Good to see you, {firstName}.</h1><p>Ready to build on your progress?</p></div><button className="button button-primary" type="button" onClick={onWorkout}>Start a workout <span aria-hidden="true">→</span></button></div>
            <div className="dashboard-stats redesigned-stats" aria-label="Workout totals">
              <article className="dashboard-stat"><span>Total workouts</span><strong>{loading ? <i className="stat-skeleton" /> : history.length}</strong><small>Saved to your history</small></article>
              <article className="dashboard-stat"><span>Total reps</span><strong>{loading ? <i className="stat-skeleton" /> : totalReps.toLocaleString()}</strong><small>Across all sessions</small></article>
              <article className="dashboard-stat"><span>Total sets</span><strong>{loading ? <i className="stat-skeleton" /> : totalSets.toLocaleString()}</strong><small>Across all sessions</small></article>
            </div>
            <div className="dashboard-main-grid">
              <div className="dashboard-left-column">
                <section className="dashboard-week premium-panel" aria-labelledby="week-title"><div className="panel-title-row"><div><span className="eyebrow">LAST 7 DAYS</span><h2 id="week-title">Your activity</h2></div><strong className="week-total">{loading ? "—" : weeklyWorkouts}<span> workouts</span></strong></div>
                  <div className="week-bars" aria-label={`${weeklyWorkouts} workouts in the last seven days`}>{weekDays.map((day, index) => <div className="week-day" key={`${day.label}-${index}`}><span className="week-count">{loading ? "—" : day.count}</span><div className={`week-track${day.count ? " has-activity" : ""}`}><span style={{ height: loading ? "0%" : `${day.count ? Math.max(12, day.count / maxDailyWorkouts * 100) : 0}%` }} /></div><span className="week-label">{day.label}</span></div>)}</div>
                </section>
                <div className="dashboard-lower-grid"><section className="dashboard-history premium-panel"><div className="panel-title-row"><div><span className="eyebrow">PICK UP WHERE YOU LEFT OFF</span><h2>Recent workouts</h2></div><button type="button" className="text-button" onClick={() => setSection("history")}>See all <span aria-hidden="true">→</span></button></div>
                  {loading ? <div className="history-loading" role="status">Loading your workouts…</div> : error ? <div className="dashboard-empty" role="alert"><p>We couldn’t load your workout history.</p><button type="button" className="button button-secondary" onClick={() => window.location.reload()}>Try again</button></div> : history.length === 0 ? <div className="dashboard-empty"><span className="empty-icon">＋</span><p>Your first workout is waiting.</p><span>Start a session and your progress will show up here.</span><button type="button" className="button button-primary" onClick={onWorkout}>Start your first workout</button></div> : <div className="history-list">{renderHistory(recent)}</div>}
                </section>
                  <section className="exercise-progress premium-panel"><div className="panel-title-row"><div><span className="eyebrow">YOUR SESSIONS</span><h2>Moves you’ve trained</h2></div></div>{exerciseTotals.length ? <div className="exercise-progress-list">{exerciseTotals.slice(0, 4).map((item) => <div key={item.name}><div><strong>{item.name}</strong><span>{item.sessions} sessions</span></div><strong>{item.reps.toLocaleString()} reps</strong></div>)}</div> : <p className="muted-copy">Your exercise progress will appear after your first session.</p>}</section>
                </div>
              </div>
              <section className="dashboard-calendar premium-panel" aria-labelledby="calendar-title"><div className="calendar-header"><div><span className="eyebrow">SHOW UP FOR YOURSELF</span><h2 id="calendar-title">Workout calendar</h2></div></div>
                <div className="calendar-month-nav"><button type="button" className="calendar-arrow" aria-label="Previous month" onClick={() => setCalendarMonth((month) => new Date(month.getFullYear(), month.getMonth() - 1, 1))}>‹</button><strong>{calendarMonth.toLocaleDateString(undefined, { month: "long", year: "numeric" })}</strong><button type="button" className="calendar-arrow" aria-label="Next month" onClick={() => setCalendarMonth((month) => new Date(month.getFullYear(), month.getMonth() + 1, 1))}>›</button></div>
                <div className="calendar-grid redesigned-calendar" role="grid" aria-label="Workout calendar">{["S", "M", "T", "W", "T", "F", "S"].map((label, index) => <span className="calendar-weekday" key={`${label}-${index}`}>{label}</span>)}{calendarCells.map((date, index) => date ? <button type="button" role="gridcell" key={localDayKey(date)} aria-label={`${date.toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" })}${workoutsByDay.has(localDayKey(date)) ? ", workout completed" : ""}`} aria-pressed={localDayKey(date) === localDayKey(selectedDay)} className={`calendar-day${workoutsByDay.has(localDayKey(date)) ? " has-workout" : ""}${localDayKey(date) === localDayKey(selectedDay) ? " is-selected" : ""}`} onClick={() => setSelectedDay(date)}><span>{date.getDate()}</span>{workoutsByDay.has(localDayKey(date)) ? <i aria-hidden="true" /> : null}</button> : <span className="calendar-empty-cell" key={`empty-${index}`} />)}</div>
                <div className="selected-day-workouts"><h3>{selectedDay.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}</h3>{selectedEntries.length ? <div className="selected-day-list">{selectedEntries.map((entry, index) => <article key={`${entry.created_at}-${entry.exercise_name}-${index}`}><strong>{entry.exercise_name}</strong><span>{entry.sets} sets · {entry.reps} reps</span></article>)}</div> : <p>No workouts on this date yet.</p>}</div>
                <button type="button" className="text-button calendar-add" onClick={() => setShowManualForm((shown) => !shown)}>{showManualForm ? "Cancel manual entry" : "+ Add a workout"}</button>
                {showManualForm ? <form className="manual-workout-form" onSubmit={(event) => void submitManualWorkout(event)}><label>Exercise<select name="exercise" required>{exerciseNames.map((name) => <option key={name}>{name}</option>)}</select></label><label>Date<input name="date" type="date" defaultValue={localDayKey(selectedDay)} required /></label><label>Reps<input name="reps" type="number" min="1" max="5000" defaultValue="1" required /></label><label>Sets<input name="sets" type="number" min="1" max="100" defaultValue="1" required /></label><label>Minutes<input name="minutes" type="number" min="0" max="1440" step="1" defaultValue="0" required /></label><button className="button button-primary" type="submit" disabled={manualSaving}>{manualSaving ? "Saving…" : "Save workout"}</button>{manualError ? <p className="manual-error" role="alert">{manualError}</p> : null}</form> : null}
              </section>
            </div>
          </> : null}

          {activeSection === "history" ? <section className="history-page-panel"><div className="dashboard-heading redesigned-dashboard-heading"><div><span className="eyebrow">YOUR TRAINING RECORD</span><h1>Workout history</h1><p>Every session you’ve saved, all in one place.</p></div><div className="history-total-pill">{history.length} sessions</div></div><div className="history-summary-row"><article><span>Total reps</span><strong>{loading ? "—" : totalReps.toLocaleString()}</strong></article><article><span>Total sets</span><strong>{loading ? "—" : totalSets.toLocaleString()}</strong></article></div>{loading ? <p className="history-loading" role="status">Loading your workouts…</p> : error ? <div className="dashboard-empty" role="alert"><p>We couldn’t load your workout history.</p><button type="button" className="button button-secondary" onClick={() => window.location.reload()}>Try again</button></div> : history.length === 0 ? <div className="dashboard-empty"><span className="empty-icon">◷</span><p>No saved workouts yet.</p><span>Your completed workouts will appear here.</span><button type="button" className="button button-primary" onClick={onWorkout}>Start a workout</button></div> : <div className="history-list history-list-page">{renderHistory(sortedHistory)}</div>}</section> : null}

          {activeSection === "profile" ? <section className="simple-settings-page"><span className="eyebrow">YOUR ACCOUNT</span><h1>Your profile</h1><p>Account details from your Google sign-in.</p><article className="profile-detail-card"><span className="profile-avatar profile-avatar-large">{firstName.slice(0, 1).toUpperCase()}</span><div><span>Display name</span><strong>{user.full_name || "Athlete"}</strong></div><div><span>Email address</span><strong>{user.email}</strong></div><button className="button button-secondary" type="button" onClick={onSignOut}>Sign out</button></article></section> : null}

          {activeSection === "settings" ? <section className="simple-settings-page"><span className="eyebrow">MAKE IT YOURS</span><h1>Settings</h1><p>Adjust how your workout coach speaks to you.</p><article className="preference-card"><div><span className="preference-icon">⌁</span><div><strong>Spoken coaching tips</strong><p>Hear form cues and workout updates while you train.</p></div></div><label className="switch-control"><input type="checkbox" checked={voiceEnabled} onChange={(event) => setVoiceEnabled(event.target.checked)} /><span aria-hidden="true" /></label></article><p className="settings-note">Your preference is saved on this device and used for your next workout.</p></section> : null}
        </div>
      </section>
    </main>
  );
}
