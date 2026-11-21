"""Run both production detectors on identical synthetic sequences."""
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "backend/tests"))
from test_detectors import DETECTOR_CASES, landmarks, set_joint_angle
from services.vision.form_score import FormScoreAccumulator

names = ["Squats", "Push-ups", "Biceps Curls (Dumbbell)", "Shoulder Press", "Lunges"]
with TemporaryDirectory() as temp:
    compile_js = """
    import fs from 'node:fs'; import ts from 'typescript';
    for (const name of ['squat','exercises']) {
      const source = fs.readFileSync('src/vision/'+name+'.ts','utf8');
      const js = ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
      fs.writeFileSync(process.argv[1]+'/'+name+'.js', js);
    }"""
    subprocess.run(["node","--input-type=module","-e",compile_js,temp],cwd=root/"frontend",check=True)
    for name, (_, cls, indices, limits) in zip(names, DETECTOR_CASES):
        detector, score = cls(), FormScoreAccumulator()
        frames, expected = [], []
        for i, degrees in enumerate([171,171,limits[0]-3,120,limits[0]-3,limits[0]-3,125,167,167]*12):
            points = landmarks()
            for side in [0,1]:
                vis = .95 if (side == int(i>=54)) else .4
                set_joint_angle(points,tuple(k+side for k in indices),degrees,vis if i%29>2 else .3)
            points[23].x += .21 if i%11<5 else 0
            points[11].visibility = .55 if i%13==0 else points[11].visibility
            frames.append([vars(p) for p in points])
            m=detector.process(points)
            score.record(m)
            expected.append({**m,"form_score":score.get_score()})
        js = """const d=require('./exercises').createDetector(process.argv[1]);
        console.log(JSON.stringify(JSON.parse(require('fs').readFileSync(0)).map(frame=>d.process(frame))))"""
        result=subprocess.run(["node","-e",js,name],cwd=temp,input=json.dumps(frames),text=True,capture_output=True,check=True)
        actual=json.loads(result.stdout)
        assert len(actual)==len(expected)
        for i,(a,e) in enumerate(zip(actual,expected)):
            assert a==e,(name,i,a,e)
        print(name,len(frames),"frames matched")

