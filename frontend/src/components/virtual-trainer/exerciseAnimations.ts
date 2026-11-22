import type { Exercise } from '../../services/api';
export const exerciseAnimations: {exercise: Exercise; clip: string; cues: string[]; custom?: boolean}[] = [
 {exercise:'Squats',clip:'Squats',cues:['Stand with your feet comfortably apart.','Lower with control, then return to standing.']},
 {exercise:'Shoulder Press',clip:'ShoulderPress',custom:true,cues:['Begin with your hands near shoulder height.','Press overhead, then lower with control.']},
 {exercise:'Push-ups',clip:'PushUps',cues:['Begin in a stable plank position.','Lower and press back up with control.']},
 {exercise:'Lunges',clip:'AlternatingLunges',custom:true,cues:['Start standing, with room to step forward.','Lower with control, then return and change legs.']},
 {exercise:'Biceps Curls (Dumbbell)',clip:'BicepsCurl',cues:['Keep your upper arms steady.','Curl, then lower with control.']},
];
