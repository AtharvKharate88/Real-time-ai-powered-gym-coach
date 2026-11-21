import { useEffect, useState } from "react";
import { draftKey, fetchDrafts, fetchWorkoutState, type Exercise, type AuthUser, type WorkoutDraft, sendCheckpoint } from "../services/api";
import LocalWorkout from "./LocalWorkout";

interface Props {
  exercise: Exercise; user: AuthUser; stream: MediaStream; onBack: () => void;
  onHistory: () => void; onDashboard: () => void; onSignOut: () => void;
}
export default function WorkoutRecovery(props: Props) {
  const {user, exercise} = props;
  const [choices, setChoices] = useState<WorkoutDraft[] | null>(null);
  const [savingId, setSavingId] = useState("");
  const [saveError, setSaveError] = useState("");
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

      }
    });
    return () => { active = false; clearTimeout(timeout); controller.abort(); };
  }, [user.id,exercise]);
  async function retrySave(d: WorkoutDraft) {
    setSavingId(d.id); setSaveError("");
    try {
      await sendCheckpoint(user.id, d.id, d.progress);
      try { localStorage.removeItem(draftKey(user.id,d.id)); } catch { /* Server has confirmed saving. */ }
      setChoices(rows => rows?.filter(row => row.id !== d.id) ?? []);
    } catch { setSaveError("Saving is still unavailable. Your completed result remains on this device."); }
    finally { setSavingId(""); }
  }
  return <>
    {choices?.some(d => d.progress.finished) && <aside className="pending-results" aria-label="Completed workouts awaiting save">
      <p>A previous workout has ended and is awaiting save.</p>
      {choices.filter(d => d.progress.finished).map(d => <button className="btn-ghost" disabled={Boolean(savingId)} key={d.id} onClick={() => void retrySave(d)}>{savingId === d.id ? "Saving…" : "Retry saving result"} · {d.progress.reps} reps</button>)}
      {offline && <p>Showing results stored on this device.</p>}
      {saveError && <p role="alert">{saveError}</p>}
    </aside>}
    <LocalWorkout {...props} draft={null} />
  </>;
}
