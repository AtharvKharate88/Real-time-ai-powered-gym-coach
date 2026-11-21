import { useEffect, useRef, useState } from "react";
import { exerciseOptions } from "./exerciseOptions";
import type { Exercise } from "../services/api";
import { createDetector } from "../vision/exercises";
import { usePoseCamera } from "../vision/usePoseCamera";
import { compareEvents, summarize, type Sample } from "../vision/benchmark";

export default function VisionBenchmark() {
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const generation = useRef(0);
  const [exercise,setExercise] = useState<Exercise>("Squats");
  const [file,setFile] = useState<File | null>(null);
  const [camera,setCamera] = useState("user");
  const [model,setModel] = useState<"full"|"lite">("full");
  const [delegate,setDelegate] = useState<"CPU"|"GPU">("CPU");
  const [running,setRunning] = useState(false);
  const [busy,setBusy] = useState(false);
  const [message,status] = useState("");
  const [repLabels,setReps] = useState("");
  const [formLabels,setForm] = useState("");
  const review = useRef<HTMLVideoElement>(null);
  const [intervalStart, setIntervalStart] = useState<number | null>(null);
  useEffect(() => {
    setReps(""); setForm(""); setIntervalStart(null);
    const el=review.current;
    if (!file || !el) return;
    const local=URL.createObjectURL(file);
    el.src=local;
    return ()=> {el.pause(); el.removeAttribute("src"); el.load(); URL.revokeObjectURL(local);};
  },[file]);
  function mark(kind: "rep" | "form") {
    const time=Number((review.current?.currentTime ?? 0).toFixed(3));
    try {
      if (kind==="rep") setReps(JSON.stringify([...JSON.parse(repLabels||"[]"),time]));
      else if (intervalStart===null) setIntervalStart(time);
      else if (time>=intervalStart) {
        setForm(JSON.stringify([...JSON.parse(formLabels||"[]"),[intervalStart,time]])); setIntervalStart(null);
      } else status("Move to the end of the form error before marking it.");
    } catch {status("Clear or correct the timestamp list before adding a mark.");}
  }
  const url = useRef("");
  const frames = useRef<Sample[]>([]);
  const events = useRef<number[]>([]);
  const detector = useRef(createDetector(exercise));
  const current = useRef({issue:false,visible:false});
  const [,refresh] = useState(0);
  const [issue,setIssue] = useState("");
  const [assessment,setAssessment] = useState("");
  const meta = useRef<Record<string,unknown>>({});
  function release() {
    stream.current?.getTracks().forEach(t=>t.stop()); stream.current=null;
    if (video.current) { video.current.pause(); video.current.srcObject=null; video.current.removeAttribute("src"); video.current.load(); }
    if (url.current) URL.revokeObjectURL(url.current);
    url.current="";
  }
  function stop(reason:string) { generation.current++; setRunning(false); setBusy(false); release(); status(reason); }
  useEffect(()=>()=>{ generation.current++; release(); },[]);
  useEffect(()=>{
    if (!running) return;
    const hidden = () => { if (document.hidden) stop("Run stopped when this tab was hidden."); };
    document.addEventListener("visibilitychange",hidden);
    const timer=setInterval(()=>refresh(n=>n+1),1000);
    return ()=>{ clearInterval(timer); document.removeEventListener("visibilitychange",hidden); };
  },[running]);
  async function start() {
    const token=++generation.current;
    setBusy(true); setAssessment(""); status("Loading camera or recording and pose model…");
    release(); frames.current=[]; events.current=[]; detector.current=createDetector(exercise);
    const v=video.current!;
    try {
      if (file) { url.current=URL.createObjectURL(file); v.src=url.current; }
      else {
        const s=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:camera},width:{ideal:640,max:640},height:{ideal:480,max:480},frameRate:{ideal:15,max:24}},audio:false});
        if (generation.current!==token) { s.getTracks().forEach(t=>t.stop()); return; }
        stream.current=s; v.srcObject=s;
        s.getVideoTracks()[0].addEventListener("ended",()=>stop("Camera disconnected."),{once:true});
      }
      meta.current={ exercise,source:file?"recording":"camera",browser:navigator.userAgent,model,delegate };
      setRunning(true);
    } catch { if (generation.current===token) stop("Camera unavailable. Check permission and the HTTPS connection."); }
  }
  usePoseCamera(video,running,(pose,mediaTime)=>{
    const m=pose ? detector.current.process(pose) : null;
    if (!m?.movement_valid) detector.current.interruptMovement();
    current.current={visible:!!m?.movement_valid,issue:!!m?.form_issue};
    if (m?.rep_completed) events.current.push(mediaTime);
    setIssue(m?.form_issue || (m?.movement_valid ? m.exercise_stage : "Move into view"));
  },()=>stop("Tracking failed on this browser."),(at,inference,media)=>{
    const f:Sample={at,inference,media,...current.current};
    frames.current.push(f);
    requestAnimationFrame(()=>{f.paint=performance.now()-at;});
    if (frames.current.length>=50000) stop("Reached the frame sample limit.");
  },()=>{
    const v=video.current!;
    void v.play().then(()=>{meta.current.width=v.videoWidth; meta.current.height=v.videoHeight; setBusy(false);status("Recording measurements.");}).catch(()=>stop("Video playback unavailable."));
  },model,delegate);
  function report() {
    const samples=frames.current;
    const t0=samples[0]?.at ?? 0;
    const minutes: Sample[][]=[];
    for (const f of samples) (minutes[Math.floor((f.at-t0)/60000)] ??=[]).push(f);
    const labels=repLabels.trim() ? JSON.parse(repLabels) : null;
    const intervals=formLabels.trim() ? JSON.parse(formLabels) : null;
    if (labels!==null && (!Array.isArray(labels)||labels.some(t=>!Number.isFinite(t)||t<0))) throw Error("Use an array of rep timestamps.");
    if (intervals!==null && (!Array.isArray(intervals)||intervals.some(v=>!Array.isArray(v)||v.length!==2||!v.every(Number.isFinite)||v[0]<0||v[1]<v[0]))) throw Error("Use pairs of start and end times.");
    let tp=0,fp=0,fn=0;
    if (intervals) for(const s of samples) {
      const issue=intervals.some(([a,b]:number[])=>s.media>=a && s.media<=b);
      if (s.issue && issue) tp++; else if (s.issue) fp++; else if (issue) fn++;
    }
    return {...meta.current,...summarize(samples),minutes:minutes.map(summarize),repTimes:events.current,
      repAccuracy:labels && compareEvents(labels,events.current),
      formAccuracy:intervals && {tp,fp,fn,precision:tp+fp?tp/(tp+fp):null,recall:tp+fn?tp/(tp+fn):null,f1:2*tp+fp+fn?2*tp/(2*tp+fp+fn):null},
      frames:samples};
  }
  function download() {
    try {
      const result=report();
      const match=result.repAccuracy;
      setAssessment(match ? `${match.matched} matched, ${match.missed} missed, ${match.falseReps} extra reps.` : "Timing report exported. Add rep labels to evaluate counting accuracy.");
      const u=URL.createObjectURL(new Blob([JSON.stringify(result)],{type:"application/json"}));
      const a=document.createElement("a");a.href=u;a.download="workout-benchmark.json";a.click();setTimeout(()=>URL.revokeObjectURL(u),5000);
    } catch(e){status(e instanceof Error?e.message:"Check the label format.");}
  }
  const stats=summarize(frames.current.slice(-100));
  return <main className="workout-page"><section className="workout-panel"><h1>Tracking benchmark</h1>
    <p>Run a live camera test or replay a local workout recording. Video stays on this device.</p>
    <div className="workout-controls"><label>Exercise<select value={exercise} disabled={running||busy} onChange={e=>setExercise(e.target.value as Exercise)}>{exerciseOptions.map(e=><option key={e.name}>{e.name}</option>)}</select></label>
    <label>Recording (optional)<input type="file" accept="video/*" disabled={running||busy} onChange={e=>setFile(e.target.files?.[0]??null)}/></label>
    <label>Model<select disabled={running||busy} value={model} onChange={e=>setModel(e.target.value as typeof model)}><option value="full">Full</option><option value="lite">Lite</option></select></label>
    <label>Inference<select disabled={running||busy} value={delegate} onChange={e=>setDelegate(e.target.value as typeof delegate)}><option>CPU</option><option>GPU</option></select></label>
    <label>Camera<select disabled={running||busy||!!file} value={camera} onChange={e=>setCamera(e.target.value)}><option value="user">Front</option><option value="environment">Rear</option></select></label>
    {running||busy?<button onClick={()=>stop("Run stopped.")}>Stop</button>:<button onClick={()=>void start()}>Start benchmark</button>}</div>
    <video ref={video} muted playsInline style={{width:"100%",maxHeight:"50vh",objectFit:"contain"}} onEnded={()=>stop("Recording complete.")} onError={()=>{if(running)stop("Unable to decode this recording.");}}/>
    <p role="status">{message} {issue}</p><p>{events.current.length} reps · {stats.processedFps??"—"} processed FPS · {stats.inferenceP95Ms??"—"} ms p95 inference</p>
    {file && <details hidden={running||busy}><summary>Mark the reps you can see in the recording</summary>
      <p>Pause at the end of each completed rep and mark it. For a form error, mark when it begins and ends.</p>
      <video ref={review} muted playsInline controls style={{width:"100%",maxHeight:"40vh"}}/>
      <button onClick={()=>mark("rep")}>Mark completed rep</button>
      <button onClick={()=>mark("form")}>{intervalStart===null?"Mark start of form error":"Mark end of form error"}</button>
    </details>}
    <label>Completed rep times in seconds <input placeholder="[3.2, 6.8, 10.1]" value={repLabels} onChange={e=>setReps(e.target.value)}/></label>
    <label>Form-error intervals in seconds <input placeholder="[[4.1, 5.3]]" value={formLabels} onChange={e=>setForm(e.target.value)}/></label>
    <button disabled={running||busy||!frames.current.length} onClick={download}>Export benchmark JSON</button>
    {assessment && <p role="status">{assessment}</p>}
  </section></main>;
}

