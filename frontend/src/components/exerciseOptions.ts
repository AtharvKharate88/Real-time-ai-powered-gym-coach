import type { Exercise } from "../services/api";

export interface ExerciseOption {
  name: Exercise;
  description: string;
  equipment: string;
  muscles: string;
  camera: string;
  difficulty: string;
  instructions: string[];
}

export const exerciseOptions: ExerciseOption[] = [
  {
    name: "Squats",
    description: "Practice a controlled descent and return to standing.",
    equipment: "No equipment",
    muscles: "Quadriceps, glutes",
    camera: "Stand sideways to the camera and keep your whole body, from hips to feet, in view.",
    difficulty: "Beginner",
    instructions: ["Stand tall before each repetition.", "Keep your hips, knees, and ankles visible.", "Descend with control, then return to standing."],
  },
  {
    name: "Push-ups",
    description: "Track your elbow bend while keeping your body aligned.",
    equipment: "No equipment",
    muscles: "Chest, shoulders, triceps",
    camera: "Place the camera to your side. Keep your shoulders, hands, and hips in view.",
    difficulty: "Beginner to intermediate",
    instructions: ["Set up in a stable plank position.", "Keep shoulders, elbows, wrists, and hips in frame.", "Lower and press back up under control."],
  },
  {
    name: "Biceps Curls (Dumbbell)",
    description: "Work through a controlled curl without swinging your torso.",
    equipment: "Dumbbells",
    muscles: "Biceps",
    camera: "Face the camera or turn slightly to the side. Keep one shoulder, elbow, and hand in view.",
    difficulty: "Beginner",
    instructions: ["Stand steady with your arm by your side.", "Keep the shoulder, elbow, and wrist visible.", "Curl and lower slowly without swinging."],
  },
  {
    name: "Shoulder Press",
    description: "Raise and lower your arms through a controlled overhead press.",
    equipment: "Bodyweight or dumbbells",
    muscles: "Shoulders, triceps",
    camera: "Face the camera and keep your shoulders, elbows, and hands in view as you press overhead.",
    difficulty: "Beginner to intermediate",
    instructions: ["Begin with your arms bent and hands near shoulder height.", "Keep both arms visible as you press overhead.", "Lower under control and avoid arching your back."],
  },
  {
    name: "Lunges",
    description: "Build a steady lunge with a controlled descent and return.",
    equipment: "No equipment",
    muscles: "Quadriceps, glutes",
    camera: "Stand sideways to the camera and keep your whole body and both legs in view.",
    difficulty: "Beginner to intermediate",
    instructions: ["Start upright with both feet visible.", "Step into a stable stance and lower with control.", "Return to standing before the next repetition."],
  },
];
