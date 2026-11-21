import json

from services.config.workout_config import PROMPT


class LLMCoach:
    def __init__(self, groq_client):
        self.client = groq_client
        self.history = []
        self.system_prompt = PROMPT

    def give_feedback(self, event, issue, exercise="unknown", metrics=None):
        context = {
            "event": event,
            "exercise": exercise,
            "form_issue": issue or "none",
            "observations": {
                key: value
                for key, value in (metrics or {}).items()
                if key in {
                    "exercise_stage", "pose_confidence", "reps", "knee_angle",
                    "back_angle", "depth_status", "elbow_angle", "body_alignment",
                    "hip_status", "extension_status", "back_arch_status",
                    "shoulder_status", "swing_status", "front_knee_angle",
                    "torso_angle", "balance_status",
                }
                and isinstance(value, (str, int, float, bool))
            },
        }
        prompt = "Current workout observation (JSON): " + json.dumps(context, ensure_ascii=False)
        if issue:
            prompt += f"\nCurrent form issue: {issue}"
        messages = [
            {"role": "system", "content": self.system_prompt},
            *self.history[-2:],
            {"role": "user", "content": prompt},
        ]
        response = self.client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=messages,
            temperature=0.25,
            max_tokens=80,
        )

        text = (response.choices[0].message.content or "").strip()
        if not text:
            return "Keep your movement controlled and steady."

        self.history.append({"role": "assistant", "content": text})
        self.history = self.history[-2:]

        return text
