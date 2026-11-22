import type { Exercise } from '../../services/api';
export const exerciseAnimations: {exercise: Exercise; clip: string; custom?: boolean}[] = [
 {exercise:'Squats',clip:'Squats'},
 {exercise:'Shoulder Press',clip:'ShoulderPress',custom:true},
 {exercise:'Push-ups',clip:'PushUps'},
 {exercise:'Lunges',clip:'AlternatingLunges',custom:true},
 {exercise:'Biceps Curls (Dumbbell)',clip:'BicepsCurl'},
];
