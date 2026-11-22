import type { Exercise } from '../../services/api';
export interface ExerciseCue { at:number; text:string }
export const exerciseAnimations: {exercise: Exercise; clip: string; cues: ExerciseCue[]; custom?: boolean}[] = [
 {exercise:'Squats',clip:'Squats',cues:[{at:0,text:'Feet about shoulder width apart.'},{at:.22,text:'Bend knees. Lower with control.'},{at:.64,text:'Press through your feet. Stand tall.'}]},
 {exercise:'Shoulder Press',clip:'ShoulderPress',custom:true,cues:[{at:0,text:'Hold the dumbbells at shoulder height.'},{at:.3,text:'Press overhead.'},{at:.72,text:'Lower to your shoulders.'}]},
 {exercise:'Push-ups',clip:'PushUps',cues:[{at:0,text:'Start in a straight plank.'},{at:.28,text:'Bend elbows. Lower your chest.'},{at:.7,text:'Press up.'}]},
 {exercise:'Lunges',clip:'AlternatingLunges',custom:true,cues:[{at:0,text:'Stand with feet under hips.'},{at:.12,text:'Step forward. Lower into a lunge.'},{at:.5,text:'Push back up. Switch legs.'}]},
 {exercise:'Biceps Curls (Dumbbell)',clip:'BicepsCurl',cues:[{at:0,text:'Hold dumbbells. Keep elbows close.'},{at:.3,text:'Curl the weights up.'},{at:.72,text:'Lower slowly to your sides.'}]},
];
