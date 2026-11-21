export interface Sample { at: number; media: number; inference: number; paint?: number; issue: boolean; visible: boolean }
export function percentile(values: number[], p: number) {
  if (!values.length) return null;
  const sorted = [...values].sort((a,b) => a-b);
  return Number(sorted[Math.ceil(sorted.length*p)-1].toFixed(2));
}
export function summarize(frames: Sample[]) {
  const gaps = frames.slice(1).map((f,i) => f.at - frames[i].at);
  const duration = frames.length > 1 ? frames[frames.length-1].at - frames[0].at : 0;
  return { frames: frames.length, visibleFrames: frames.filter(f=>f.visible).length,
    processedFps: duration ? Number((gaps.length*1000/duration).toFixed(2)) : null,
    inferenceP50Ms: percentile(frames.map(f=>f.inference),0.5), inferenceP95Ms: percentile(frames.map(f=>f.inference),0.95),
    gapP95Ms: percentile(gaps,0.95), gapMaxMs: gaps.reduce((a,b)=>Math.max(a,b),0),
    frameToNextAnimationP95Ms: percentile(frames.flatMap(f=>f.paint === undefined ? [] : [f.paint]),0.95) };
}
export function compareEvents(expected: number[], observed: number[], tolerance = 0.5) {
  const labels = [...expected].sort((a,b)=>a-b);
  let i = 0, k = 0;
  const delays: number[] = [];
  while (i < labels.length && k < observed.length) {
    const offset = observed[k]-labels[i];
    if (offset < -tolerance) k++;
    else if (offset > tolerance) i++;
    else { delays.push(offset*1000); i++; k++; }
  }
  return { matched: delays.length, missed: labels.length-delays.length, falseReps: observed.length-delays.length,
    detectionOffsetMedianMs: percentile(delays,0.5), toleranceSeconds: tolerance };
}

