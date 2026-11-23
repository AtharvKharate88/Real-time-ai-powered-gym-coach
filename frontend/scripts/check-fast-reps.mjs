import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

const source = await readFile(new URL('../src/vision/squat.ts', import.meta.url), 'utf8');
const { outputText } = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } });
const { RepTracker } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);
function run(values, { low = 100, high = 160, count = 'up' } = {}) {
  const tracker = new RepTracker();
  for (const value of values) {
    if (value === null) tracker.interruptMovement();
    else tracker.updateStage(value, low, high, 'down', 'up', count);
  }
  return tracker.reps;
}
assert.equal(run([170,170,145,112,95,120,150,165]), 1, 'one-frame endpoints with approach evidence');
assert.equal(run([170,170,145,112,95,120,150,165,140,110,95,125,150,165]), 2, 'consecutive fast reps');
assert.equal(run([170,170,140,120,110,125,155,170,170]), 0, 'partial movement');
assert.equal(run([170,170,95,170,170]), 0, 'isolated low-angle glitch');
assert.equal(run([95,95,120,150,170,170]), 0, 'starting midway does not count');
assert.equal(run([170,170,112,95,null,150,170,170]), 0, 'lost tracking cancels incomplete rep');
assert.equal(run([170,170,112,95,95,95,95]), 0, 'holding endpoint does not count');
assert.equal(run([170,170,62,45,80,148,165], { low: 50 }), 1, 'curl range with brief contraction');
assert.equal(run([70,70,120,150,165,120,102,85], { low: 90, count: 'down' }), 1, 'press counts return to baseline');
console.log('9 rep tracking regression cases passed. Synthetic angle checks do not establish real-device accuracy.');
