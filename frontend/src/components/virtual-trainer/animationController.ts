import { AnimationMixer, LoopRepeat, type AnimationClip, type Object3D, type AnimationAction } from 'three';
export class AnimationController {
 mixer: AnimationMixer; current?: AnimationAction; private elapsed=0; private readonly demoCycles=2;
 constructor(private root:Object3D, private clips:AnimationClip[]) { this.mixer=new AnimationMixer(root); }
 play(name:string) {
  const clip=this.clips.find(c=>c.name===name); if(!clip) throw new Error('This demonstration is unavailable.');
  const old=this.current; const next=this.mixer.clipAction(clip);
  if(old===next) old.stop(); else old?.fadeOut(.2);
  this.elapsed=0; next.reset().setLoop(LoopRepeat,this.demoCycles); next.clampWhenFinished=true; if(old && old!==next) next.fadeIn(.2); else next.stopFading().setEffectiveWeight(1);
  next.play(); this.current=next; this.mixer.update(.001);
 }
 update(delta:number,playing:boolean,speed:number) { if(playing) { const step=Math.min(delta,.1)*speed; const total=this.current ? this.current.getClip().duration*this.demoCycles : 0; this.elapsed=Math.min(total,this.elapsed+step); this.mixer.update(step); } }
 progress() { const total=this.current ? this.current.getClip().duration*this.demoCycles : 0; return total ? Math.min(1,this.elapsed/total) : 0; }
 dispose(){this.mixer.stopAllAction();this.mixer.uncacheRoot(this.root);}
}
