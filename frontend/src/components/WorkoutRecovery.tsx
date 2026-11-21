import { useEffect, useState } from "react";
import { draftKey, fetchDrafts, fetchWorkoutState, type Exercise, type AuthUser, type WorkoutDraft } from "../services/api";
import LocalWorkout from "./LocalWorkout";

interface Props {
  exercise: Exercise; user: AuthUser; stream: MediaStream; onBack: () => void;
  onHistory: () => void; onDashboard: () => void; onSignOut: () => void;
}
export default function WorkoutRecovery(props: Props) {
  const {user, exercise} = props;
  const [choices, setChoices] = useState<WorkoutDraft[] | null>(null);
  const [selected, select] = useState<WorkoutDraft | null | undefined>(undefined);
  const [offline, setOffline] = useState(false);
  useEffect(() => {
    let active = true;
    const drafts = new Map<string,WorkoutDraft>();
    const merge = (d: WorkoutDraft) => {
      const p = d?.progress;
      if (p?.exercise !== exercise || typeof d.id !== "string" || !/^[0-9a-f-]{36}$/i.test(d.id) || typeof p.finished !== "boolean") return;
      const bounds = {revision:2_000_000_000,reps:2500,target_sets:50,reps_per_set:50,elapsed_seconds:86400,
        good_frames:2_000_000,warning_frames:2_000_000,incorrect_frames:2_000_000};
      if (Object.entries(bounds).some(([k,max]) => {
        const n=p[k as keyof typeof bounds];
        return !Number.isInteger(n) || n<0 || n>max;
      }) || !p.target_sets || !p.reps_per_set || !p.revision || p.reps>p.target_sets*p.reps_per_set) return;
      if ((drafts.get(d.id)?.progress.revision ?? -1) < p.revision) drafts.set(d.id,d);
    };
    try {
      const old = JSON.parse(sessionStorage.getItem("gym-local-squats:"+user.id) ?? "null");
      if (old?.summary && exercise === "Squats") {
        const migrated = {id: old.id, progress: {...old.summary, exercise, incorrect_frames:0, revision:1, finished:old.finished}};
        if (!localStorage.getItem(draftKey(user.id,old.id))) localStorage.setItem(draftKey(user.id,old.id),JSON.stringify(migrated));
        sessionStorage.removeItem("gym-local-squats:"+user.id);
      }
      for (const k of Object.keys(localStorage)) if (k.startsWith(draftKey(user.id,""))) {
        try { merge(JSON.parse(localStorage.getItem(k) ?? "null")); } catch { /* Ignore malformed entries. */ }
      }
    } catch { /* Browser may restrict storage. */ }
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 4000);
    fetchDrafts(user.id,controller.signal).then(async rows => {
      const onServer = new Set(rows.map(row => row.id));
      rows.forEach(merge);
      await Promise.all([...drafts.keys()].filter(id => !onServer.has(id)).map(async id => {
        const remote = await fetchWorkoutState(user.id,id,controller.signal);
        if (active && remote.finished) {
          drafts.delete(id);
          try { localStorage.removeItem(draftKey(user.id,id)); } catch { /* Recovery still works on the server. */ }
        }
      }));
    }).catch(() => {
      if (active) setOffline(true);
    }).finally(() => {
      clearTimeout(timeout);
      if (active) {
        setChoices([...drafts.values()]);
        if (!drafts.size) select(null);
      }
    });
    return () => { active = false; clearTimeout(timeout); controller.abort(); };
  }, [user.id,exercise]);
  if (selected !== undefined) return <LocalWorkout {...props} draft={selected} />;
  return <main className="workout-page"><section className="workout-panel"><h1>{exercise}</h1>
    {choices === null ? <p role="status">Checking for unfinished workouts…</p> : <>
      {offline && <p>Showing workouts stored on this device.</p>}
      {choices.map(d => <button className="btn-primary" key={d.id} onClick={() => select(d)}>
        {d.progress.finished ? "Retry save" : "Recover workout"} · {d.progress.reps} reps · {d.progress.elapsed_seconds}s
      </button>)}
      <button className="btn-ghost" onClick={() => select(null)}>Start a separate workout</button>
    </>}
    <button className="btn-ghost" onClick={props.onBack}>Return to camera setup</button>
  </section></main>;
}

