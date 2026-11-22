import { Component, Suspense, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Canvas, createPortal, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, useGLTF, Html, useProgress } from '@react-three/drei';
import { AnimationController } from './animationController';
import { exerciseAnimations } from './exerciseAnimations';
import TrainerControls from './TrainerControls';
import type { Exercise } from '../../services/api';
const asset=import.meta.env.BASE_URL+'models/trainer/trainer.glb';
function ModelLoading(){const {progress}=useProgress();return <div className="trainer-fallback" role="status"><span>Loading trainer… {Math.round(progress)}%</span><progress max={100} value={progress}/></div>;}
class ViewerBoundary extends Component<{children:ReactNode},{failed:boolean}> {
 state={failed:false}; static getDerivedStateFromError(){return {failed:true};}
 render(){return this.state.failed?<div className="trainer-fallback" role="alert">The 3D viewer could not load. Check your connection and WebGL support, then reopen Virtual Trainer.</div>:this.props.children;}
}
function Character({clip,replay,playing,speed,onProgress,onReady,exercise}:{clip:string;replay:number;playing:boolean;speed:number;onProgress:(n:number)=>void;onReady:()=>void;exercise:Exercise}) {
 const invalidate=useThree(s=>s.invalidate);
 const {scene,animations}=useGLTF(asset,import.meta.env.BASE_URL+"draco/",true); const controller=useMemo(()=>new AnimationController(scene,animations),[scene,animations]); const elapsed=useRef(0);
 useEffect(()=>{controller.play(clip);invalidate();onReady();return ()=>{};},[controller,clip,replay,onReady,invalidate]);
 useEffect(()=>()=>controller.dispose(),[controller]);
 useFrame((_,delta)=>{controller.update(delta,playing,speed);elapsed.current+=delta;if(elapsed.current>.1){elapsed.current=0;onProgress(controller.progress());}});
 const isWeights=exercise==='Shoulder Press'||exercise==='Biceps Curls (Dumbbell)';
 const leftHand=scene.getObjectByName('mixamorig5LeftHand'),rightHand=scene.getObjectByName('mixamorig5RightHand');
 return <><primitive object={scene} dispose={null}/>{isWeights&&<>
  {leftHand&&<Dumbbell hand={leftHand}/>}{rightHand&&<Dumbbell hand={rightHand}/>}
 </> }</>;
}
function Dumbbell({hand}:{hand:import('three').Object3D}) {
 return createPortal(<group position={[0,8,0]} scale={100}>
  <mesh rotation={[0,0,Math.PI/2]}><cylinderGeometry args={[.012,.012,.14,16]}/><meshStandardMaterial color="#b6ff3b" emissive="#4b7015" emissiveIntensity={.3} metalness={.45} roughness={.3}/></mesh>
  {[-.095,.095].map(x=><mesh key={x} position={[x,0,0]} rotation={[0,0,Math.PI/2]}><cylinderGeometry args={[.045,.045,.05,20]}/><meshStandardMaterial color="#69737b" metalness={.45} roughness={.35}/></mesh>)}
 </group>,hand);
}

export default function VirtualTrainer({onWorkout,initialExercise,compact=false}:{onWorkout:(exercise:Exercise)=>void;initialExercise?:Exercise;compact?:boolean}) {
 const [index,setIndex]=useState(Math.max(0,exerciseAnimations.findIndex(x=>x.exercise===initialExercise))),[playing,setPlaying]=useState(false),[speed,setSpeed]=useState(1),[replay,setReplay]=useState(0),[progress,setProgress]=useState(0),[ready,setReady]=useState(false);
 const [selected,setSelected]=useState(Boolean(initialExercise));
 const loaded=useCallback(()=>setReady(true),[]);
 const item=exerciseAnimations[index];
 useEffect(()=>{const hide=()=>{if(document.hidden)setPlaying(false);};document.addEventListener('visibilitychange',hide);return()=>document.removeEventListener('visibilitychange',hide);},[]);
 useEffect(()=>{if(progress>=1)setPlaying(false);},[progress]);
 function restart(i=index){setSelected(true);setIndex(i);setProgress(0);setReplay(r=>r+1);setPlaying(true);}
 return <section className={`virtual-trainer${compact?" trainer-compact":""}`}>{!compact&&<><span className="eyebrow">WATCH. LEARN. MOVE.</span><h1>Your virtual trainer.</h1><p>Explore the movement, then take it to your workout.</p></>}<div className="trainer-layout"><div><div className="trainer-stage"><ViewerBoundary><Suspense fallback={<ModelLoading/>}><Canvas frameloop={playing?"always":"demand"} dpr={[1,1.5]} camera={{position:[2.3,1.3,3.5],fov:42}} gl={{antialias:true}}><color attach="background" args={['#11191c']}/><ambientLight intensity={1.8}/><directionalLight position={[3,5,4]} intensity={3}/><Suspense fallback={<Html center>Loading character…</Html>}><Character clip={selected?item.clip:'Idle'} replay={replay} playing={playing} speed={speed} onProgress={setProgress} onReady={loaded} exercise={item.exercise}/></Suspense><OrbitControls target={[0,.9,0]} enablePan={false} minDistance={2.5} maxDistance={5} maxPolarAngle={Math.PI/2}/><gridHelper args={[6,24,'#33452b','#202c26']}/></Canvas></Suspense></ViewerBoundary></div><TrainerControls playing={playing} onPlay={()=>!selected||progress>=1?restart():setPlaying(v=>!v)} onReplay={()=>restart()} speed={speed} onSpeed={setSpeed} progress={progress} ready={ready}/></div><aside><h2>{item.exercise}</h2><p>Watch the movement and follow the on-screen controls.</p>{!compact&&exerciseAnimations.map((x,i)=><button key={x.clip} aria-pressed={i===index} className="trainer-exercise" onClick={()=>{restart(i);}}><span>{x.exercise}</span><small>How to do →</small></button>)}{item.custom&&<p className="trainer-review-note">Custom animation · technique review pending.</p>}<button className="button button-primary" onClick={()=>onWorkout(item.exercise)}>Practice this exercise →</button><p className="trainer-review-note">Movement illustration only. Your range of motion may differ.</p></aside></div></section>;
}
