import { Component, Suspense, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, useGLTF, Html } from '@react-three/drei';
import { AnimationController } from './animationController';
import { exerciseAnimations } from './exerciseAnimations';
import TrainerControls from './TrainerControls';
import type { Exercise } from '../../services/api';
const asset=import.meta.env.BASE_URL+'models/trainer/trainer.glb';
class ViewerBoundary extends Component<{children:ReactNode},{failed:boolean}> {
 state={failed:false}; static getDerivedStateFromError(){return {failed:true};}
 render(){return this.state.failed?<div className="trainer-fallback" role="alert">The 3D viewer could not load. Check your connection and WebGL support, then reopen Virtual Trainer.</div>:this.props.children;}
}
function Character({clip,replay,playing,speed,onProgress,onReady}:{clip:string;replay:number;playing:boolean;speed:number;onProgress:(n:number)=>void;onReady:()=>void}) {
 const invalidate=useThree(s=>s.invalidate);
 const {scene,animations}=useGLTF(asset); const controller=useMemo(()=>new AnimationController(scene,animations),[scene,animations]); const elapsed=useRef(0);
 useEffect(()=>{controller.play(clip);invalidate();onReady();return ()=>{};},[controller,clip,replay,onReady,invalidate]);
 useEffect(()=>()=>controller.dispose(),[controller]);
 useFrame((_,delta)=>{controller.update(delta,playing,speed);elapsed.current+=delta;if(elapsed.current>.1){elapsed.current=0;onProgress(controller.progress());}});
 return <primitive object={scene} dispose={null}/>;
}

export default function VirtualTrainer({onWorkout}:{onWorkout:(exercise:Exercise)=>void}) {
 const [index,setIndex]=useState(0),[playing,setPlaying]=useState(false),[speed,setSpeed]=useState(1),[replay,setReplay]=useState(0),[progress,setProgress]=useState(0),[ready,setReady]=useState(false),[voice,setVoice]=useState(false);
 const [selected,setSelected]=useState(false);
 const loaded=useCallback(()=>setReady(true),[]);
 const item=exerciseAnimations[index]; const spoken=useRef(new Set<number>());
 useEffect(()=>{const hide=()=>{if(document.hidden){setPlaying(false);window.speechSynthesis?.cancel();}};document.addEventListener('visibilitychange',hide);return()=>{document.removeEventListener('visibilitychange',hide);window.speechSynthesis?.cancel();};},[]);
 useEffect(()=>{if(!playing||!voice){window.speechSynthesis?.cancel();return;} const phase=progress<.3?0:1;if(!spoken.current.has(phase)&&window.speechSynthesis&&!window.speechSynthesis.speaking){spoken.current.add(phase);window.speechSynthesis.speak(new SpeechSynthesisUtterance(item.cues[phase]));}},[playing,voice,progress,item]);
 useEffect(()=>{if(progress>=1)setPlaying(false);},[progress]);
 function restart(i=index){setSelected(true);window.speechSynthesis?.cancel();spoken.current.clear();setIndex(i);setProgress(0);setReplay(r=>r+1);setPlaying(true);}
 return <section className="virtual-trainer"><span className="eyebrow">WATCH. LEARN. MOVE.</span><h1>Your virtual trainer.</h1><p>Explore the movement, then take it to your workout.</p><div className="trainer-layout"><div><div className="trainer-stage"><ViewerBoundary><Suspense fallback={<div className="trainer-fallback" role="status">Loading your trainer…</div>}><Canvas frameloop={playing?"always":"demand"} dpr={[1,1.5]} camera={{position:[2.3,1.3,3.5],fov:42}} gl={{antialias:true}}><color attach="background" args={['#11191c']}/><ambientLight intensity={1.8}/><directionalLight position={[3,5,4]} intensity={3}/><Suspense fallback={<Html center>Loading character…</Html>}><Character clip={selected?item.clip:'Idle'} replay={replay} playing={playing} speed={speed} onProgress={setProgress} onReady={loaded}/></Suspense><OrbitControls target={[0,.9,0]} enablePan={false} minDistance={2.5} maxDistance={5} maxPolarAngle={Math.PI/2}/><gridHelper args={[6,24,'#33452b','#202c26']}/></Canvas></Suspense></ViewerBoundary></div><TrainerControls playing={playing} onPlay={()=>!selected||progress>=1?restart():setPlaying(v=>!v)} onReplay={()=>restart()} speed={speed} onSpeed={setSpeed} voice={voice} onVoice={setVoice} progress={progress} ready={ready}/></div><aside><h2>{item.exercise}</h2><p>Drag to rotate the view. Use slow motion to follow each phase.</p>{exerciseAnimations.map((x,i)=><button key={x.clip} aria-pressed={i===index} className="trainer-exercise" onClick={()=>{restart(i);}}><span>{x.exercise}</span><small>How to do →</small></button>)}{item.custom&&<p className="trainer-review-note">Custom animation · technique review pending.</p>}<button className="button button-primary" onClick={()=>onWorkout(item.exercise)}>Practice this exercise →</button><p className="trainer-review-note">Movement illustration only. Your range of motion may differ. Voice timing is approximate.</p></aside></div></section>;
}
