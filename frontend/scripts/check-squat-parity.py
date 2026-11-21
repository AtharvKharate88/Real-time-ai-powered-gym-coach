"""Compare the browser detector with the production Python detector on identical frames."""
import json
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "backend" / "tests"))
from test_detectors import SquatDetector, landmarks, set_joint_angle
from services.vision.form_score import FormScoreAccumulator

reference = SquatDetector()
score = FormScoreAccumulator()
frames, expected = [], []
for index, degrees in enumerate([171, 171, 96, 120, 96, 96, 125, 167, 167] * 8):
    points = landmarks()
    visible = 0.65 if 20 <= index < 26 else 0.95
    set_joint_angle(points, (23, 25, 27), degrees, visible if index < 40 else 0.3)
    set_joint_angle(points, (24, 26, 28), degrees, visible if index >= 40 else 0.3)
    points[12 if index >= 40 else 11].visibility = 0.4 if index % 8 == 3 else 0.9
    frames.append([vars(point) for point in points])
    metrics = reference.process(points)
    score.record(metrics)
    expected.append({**metrics, "form_score": score.get_score()})

runner = """
import fs from 'node:fs';
import ts from 'typescript';
const source = fs.readFileSync('src/vision/squat.ts', 'utf8');
const js = ts.transpileModule(source, {compilerOptions: {target: ts.ScriptTarget.ES2020,
  module: ts.ModuleKind.ESNext}}).outputText;
const {SquatDetector} = await import('data:text/javascript;base64,' + Buffer.from(js).toString('base64'));
const detector = new SquatDetector();
console.log(JSON.stringify(JSON.parse(fs.readFileSync(0, 'utf8')).map(frame => detector.process(frame))));
"""
result = subprocess.run(["node", "--input-type=module", "-e", runner], cwd=root / "frontend",
                        input=json.dumps(frames), capture_output=True, text=True, check=True)
actual = json.loads(result.stdout)
assert len(expected) == len(actual)
for index, (python_frame, browser_frame) in enumerate(zip(expected, actual)):
    assert python_frame == browser_frame, (index, python_frame, browser_frame)
print(f"{len(actual)} synthetic frames matched, including reps, feedback and form score.")
