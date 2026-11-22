import { AnimationMixer, LoopOnce, type AnimationClip, type Object3D, type AnimationAction } from 'three';
export class AnimationController {
 mixer: AnimationMixer; current?: AnimationAction;
 constructor(private root:Object3D, private clips:AnimationClip[]) { this.mixer=new AnimationMixer(root); }
 play(name:string) {
  const clip=this.clips.find(c=>c.name===name); if(!clip) throw new Error('This demonstration is unavailable.');
  const old=this.current; const next=this.mixer.clipAction(clip);
  if(old===next) old.stop(); else old?.fadeOut(.2);
  next.reset().setLoop(LoopOnce,1); next.clampWhenFinished=true; if(old && old!==next) next.fadeIn(.2); else next.stopFading().setEffectiveWeight(1);
  next.play(); this.current=next; this.mixer.update(.001);
 }
 update(delta:number,playing:boolean,speed:number) { if(playing) this.mixer.update(Math.min(delta,.1)*speed); }
 progress() {return this.current ? Math.min(1,this.current.time/this.current.getClip().duration):0;}
 dispose(){this.mixer.stopAllAction();this.mixer.uncacheRoot(this.root);}
}
