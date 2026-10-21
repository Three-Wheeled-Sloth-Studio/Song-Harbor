/**
 * Song Harbor section-aware automation primitives.
 *
 * Time is always in SONG seconds. The caller maps it onto the shared
 * AudioContext clock at each play/seek/loop restart. Automation is declarative
 * and source audio remains unchanged.
 */
export type AutomationParameter = "gain" | "pan";
export type AutomationCurve = "linear" | "smooth";
export type SectionTarget = {
  sectionId: string;
  start: number;
  end: number;
  value: number;
  transitionSeconds?: number;
  curve?: AutomationCurve;
};
export type AutomationPoint = {time:number;value:number};
const EPSILON=1e-6;

export function compileSectionAutomation(
  targets: SectionTarget[],
  initialValue: number,
  bounds: {min:number;max:number},
  defaultTransitionSeconds=1,
): AutomationPoint[] {
  if(!Number.isFinite(initialValue)||initialValue<bounds.min||initialValue>bounds.max)
    throw Error("Invalid initial automation value");
  if(!Number.isFinite(defaultTransitionSeconds)||defaultTransitionSeconds<0)
    throw Error("Invalid automation transition duration");
  const sorted=[...targets].sort((a,b)=>a.start-b.start);
  const points:AutomationPoint[]=[{time:0,value:initialValue}];
  let previousEnd=0;
  for(const target of sorted){
    if(!Number.isFinite(target.start)||!Number.isFinite(target.end)||
       target.start<0||target.end<=target.start||target.start<previousEnd-EPSILON)
      throw Error("Section automation requires nonoverlapping positive intervals");
    if(!Number.isFinite(target.value)||target.value<bounds.min||target.value>bounds.max)
      throw Error("Section automation target is outside parameter bounds");
    const transition=target.transitionSeconds??defaultTransitionSeconds;
    if(!Number.isFinite(transition)||transition<0)
      throw Error("Invalid section transition");
    const rampEnd=Math.min(target.end,target.start+transition);
    // Anchor at the actual previous value, including when a transition is
    // interrupted by a short section. No discontinuity at the boundary.
    const anchor=valueAt(points,target.start);
    points.push({time:target.start,value:anchor});
    if(rampEnd>target.start+EPSILON){
      if(target.curve==="smooth"){
        // Piecewise smoothstep approximation (C1 at both endpoints).
        for(let i=1;i<=16;i++){
          const x=i/16;
          points.push({time:target.start+(rampEnd-target.start)*x,
            value:anchor+(target.value-anchor)*x*x*(3-2*x)});
        }
      }else{
        points.push({time:rampEnd,value:target.value});
      }
    }else{
      // A zero-duration target is represented by an effectively immediate
      // AudioParam transition; no setValueAtTime jump during playback.
      points.push({time:target.start+EPSILON,value:target.value});
    }
    previousEnd=target.end;
  }
  return points;
}

export function valueAt(points:readonly AutomationPoint[],time:number):number {
  if(!points.length)throw Error("Missing automation points");
  if(time<=points[0].time)return points[0].value;
  for(let i=1;i<points.length;i++){
    const before=points[i-1],after=points[i];
    if(time<=after.time){
      const fraction=(time-before.time)/Math.max(EPSILON,after.time-before.time);
      return before.value+(after.value-before.value)*Math.max(0,Math.min(1,fraction));
    }
  }
  return points[points.length-1].value;
}

/** Reschedule following every shared-clock transport restart (play/seek/loop).
 * The caller must manage manual base levels separately from automated values.
 */
export function scheduleAutomation(
  param:AudioParam,
  points:readonly AutomationPoint[],
  offsetSeconds:number,
  contextStartSeconds:number,
){
  if(!points.length)return;
  param.cancelScheduledValues(contextStartSeconds);
  param.setValueAtTime(valueAt(points,offsetSeconds),contextStartSeconds);
  for(const point of points){
    if(point.time<=offsetSeconds)continue;
    param.linearRampToValueAtTime(
      point.value,contextStartSeconds+point.time-offsetSeconds);
  }
}
