import type { Exercise } from "../services/api";

type Point = readonly [number, number];
type Pose = {
  head: Point;
  shoulder: Point;
  elbow: Point;
  hand: Point;
  hip: Point;
  knee: Point;
  foot: Point;
  farElbow?: Point;
  farHand?: Point;
  farKnee?: Point;
  farFoot?: Point;
};

const poses: Record<Exercise, Pose> = {
  "Squats": {
    head: [115, 39], shoulder: [112, 62], elbow: [135, 77], hand: [151, 73], hip: [111, 91], knee: [139, 113], foot: [159, 132],
    farElbow: [91, 78], farHand: [78, 73], farKnee: [91, 113], farFoot: [74, 130],
  },
  "Push-ups": {
    head: [50, 73], shoulder: [75, 82], elbow: [80, 111], hand: [102, 126], hip: [121, 88], knee: [159, 94], foot: [190, 98],
    farElbow: [75, 119], farHand: [102, 132], farKnee: [161, 103], farFoot: [192, 106],
  },
  "Biceps Curls (Dumbbell)": {
    head: [116, 31], shoulder: [115, 56], elbow: [91, 82], hand: [104, 64], hip: [116, 91], knee: [110, 120], foot: [106, 145],
    farElbow: [139, 81], farHand: [127, 63], farKnee: [124, 120], farFoot: [128, 145],
  },
  "Shoulder Press": {
    head: [116, 37], shoulder: [116, 62], elbow: [91, 42], hand: [85, 17], hip: [116, 96], knee: [110, 122], foot: [106, 147],
    farElbow: [141, 42], farHand: [147, 17], farKnee: [123, 122], farFoot: [127, 147],
  },
  "Lunges": {
    head: [116, 34], shoulder: [116, 59], elbow: [93, 77], hand: [84, 88], hip: [116, 91], knee: [89, 111], foot: [72, 130],
    farElbow: [139, 77], farHand: [148, 87], farKnee: [151, 117], farFoot: [178, 129],
  },
};

function line(from: Point, to: Point, className: string) {
  return <line className={className} x1={from[0]} y1={from[1]} x2={to[0]} y2={to[1]} />;
}

export default function ExerciseIllustration({ exercise, className = "" }: { exercise: Exercise; className?: string }) {
  const pose = poses[exercise];
  const farElbow = pose.farElbow ?? [pose.shoulder[0] + 18, pose.shoulder[1] + 18] as Point;
  const farHand = pose.farHand ?? [farElbow[0] + 10, farElbow[1] + 16] as Point;
  const farKnee = pose.farKnee ?? [pose.hip[0] + 14, pose.hip[1] + 27] as Point;
  const farFoot = pose.farFoot ?? [farKnee[0] + 18, farKnee[1] + 20] as Point;

  return (
    <svg className={`exercise-art ${className}`} viewBox="0 0 232 164" role="img" aria-label={`${exercise} illustration`}>
      <defs>
        <linearGradient id={`art-bg-${exercise.replace(/\W/g, "")}`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#1d2730" />
          <stop offset="1" stopColor="#11171d" />
        </linearGradient>
      </defs>
      <rect width="232" height="164" rx="18" fill={`url(#art-bg-${exercise.replace(/\W/g, "")})`} />
      <circle cx="178" cy="39" r="27" fill="#a3e635" opacity=".08" />
      <path d="M20 145h192" stroke="#33404b" strokeWidth="1" />
      <g fill="none" strokeLinecap="round" strokeLinejoin="round">
        {line(pose.shoulder, pose.elbow, "athlete-limb far-limb")}
        {line(pose.elbow, pose.hand, "athlete-limb far-limb")}
        {line(pose.hip, pose.knee, "athlete-limb far-limb")}
        {line(pose.knee, pose.foot, "athlete-limb far-limb")}
        {line(pose.shoulder, pose.farElbow ?? farElbow, "athlete-limb")}
        {line(pose.farElbow ?? farElbow, pose.farHand ?? farHand, "athlete-limb")}
        {line(pose.hip, pose.farKnee ?? farKnee, "athlete-limb")}
        {line(pose.farKnee ?? farKnee, pose.farFoot ?? farFoot, "athlete-limb")}
        <path className="athlete-shirt" d={`M${pose.shoulder[0]} ${pose.shoulder[1]} L${pose.hip[0]} ${pose.hip[1]}`} />
      </g>
      <circle cx={pose.head[0]} cy={pose.head[1]} r="12" className="athlete-head" />
      <circle cx={pose.shoulder[0]} cy={pose.shoulder[1]} r="4" className="athlete-joint" />
      <circle cx={pose.hip[0]} cy={pose.hip[1]} r="4" className="athlete-joint" />
      <circle cx={pose.elbow[0]} cy={pose.elbow[1]} r="3" className="athlete-joint" />
      <circle cx={pose.knee[0]} cy={pose.knee[1]} r="3" className="athlete-joint" />
    </svg>
  );
}
