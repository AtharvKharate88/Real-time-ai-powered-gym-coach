EXERCISE_OPTIONS=[
    "Squats",
    "Push-ups",
    "Biceps Curls (Dumbbell)",
    "Shoulder Press",
    "Lunges"
]

POSE_CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),       # Shoulders & Arms
    (11, 23), (12, 24), (23, 24),                           # Torso / Hips
    (23, 25), (24, 26), (25, 27), (26, 28), (27, 29), (28, 30), (29, 31), (30, 32), (27, 31), (28, 32)  # Legs
]


METRICS_FIELDS = {
    "Squats": {
        "knee_angle": 0,
        "back_angle": 0,
        "depth_status": "N/A",
    },
    "Push-ups": {
        "elbow_angle": 0,
        "body_alignment": "N/A",
        "hip_status": "N/A",
    },
    "Biceps Curls (Dumbbell)": {
        "elbow_angle": 0,
        "shoulder_status": "N/A",
        "swing_status": "N/A",
    },
    "Shoulder Press": {
        "elbow_angle": 0,
        "extension_status": "N/A",
        "back_arch_status": "N/A",
    },
    "Lunges": {
        "front_knee_angle": 0,
        "torso_angle": 0,
        "balance_status": "N/A",
    },
}

PROMPT = (
    "You are Apna AI Coach, a professional AI gym trainer monitoring a user's workout via live camera.\n\n"
    "Give one useful spoken coaching cue only when the input contains a form issue or a workout milestone.\n"
    "Use the exercise, phase, and measurements to make the cue specific. For a form issue, tell the athlete exactly what to change and how; briefly explain the benefit when useful.\n"
    "Use 1–2 natural sentences and 15–28 words total. Prefer one main correction over a list. Use direct second-person language, common words, and a calm encouraging tone.\n"
    "Use only the supplied issue and measurements. Do not invent observations, repeat an older cue, diagnose an injury, or give medical advice. Prioritize balance and controlled movement.\n"
    "Do not greet, ask questions, use emojis, or add generic filler. For no_pose_detected, give one short framing instruction. For start/set/finish events, use a concise milestone message."
)

