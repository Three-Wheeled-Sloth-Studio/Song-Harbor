import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import ts from "typescript";
const source=fs.readFileSync(new URL("../src/EchoDelay.ts",import.meta.url),"utf8");
const settings={compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}};
const automation=fs.readFileSync(new URL("../src/SectionAutomation.ts",import.meta.url),"utf8");
const automationUrl="data:text/javascript;base64,"+Buffer.from(ts.transpileModule(automation,settings).outputText).toString("base64");
const js=ts.transpileModule(source.replace('from "./SectionAutomation";','from "'+automationUrl+'";'),settings).outputText;
const {validateEcho,echoTailSeconds,scheduleSectionEcho}=await import(
  "data:text/javascript;base64,"+Buffer.from(js).toString("base64")
);
const echo={delayMs:180,wet:.18,feedback:.25,lowpassHz:6500};
test("echo input bounds reject unstable feedback and invalid delay",()=>{
  assert.deepEqual(validateEcho(echo),echo);
  assert.throws(()=>validateEcho({...echo,feedback:.9}));
  assert.throws(()=>validateEcho({...echo,delayMs:0}));
  assert.throws(()=>validateEcho({...echo,wet:1.2}));
  assert.throws(()=>validateEcho({...echo,lowpassHz:Infinity}));
});
test("echo tails cover repeats and are bounded",()=>{
  assert.equal(echoTailSeconds({...echo,wet:0}),0);
  assert.equal(echoTailSeconds({...echo,feedback:0}),.18);
  assert.ok(echoTailSeconds(echo)>.18);
  assert.ok(echoTailSeconds({...echo,delayMs:2000,feedback:.8})<=8);
});
test("echo exports keep source delay distinct from stem offset",()=>{
  const code=fs.readFileSync(new URL("../src/SharedClockAudition.ts",import.meta.url),"utf8");
  assert.match(code,/createEchoStage\(this\.context/);
  assert.match(code,/createEchoStage\(offline/);
  assert.match(code,/setStemTimeOffsets/);
  assert.match(code,/setEchoSettings/);
});

const fakeParam=()=>{
  const calls=[];
  return {calls,cancelScheduledValues(t){calls.push(["cancel",t]);},
    setValueAtTime(v,t){calls.push(["set",v,t]);},
    linearRampToValueAtTime(v,t){calls.push(["ramp",v,t]);}};
};
test("section changes inherit previous echo and wet zero fades it out",()=>{
  const stage={delay:{delayTime:fakeParam()},feedback:{gain:fakeParam()},
    filter:{frequency:fakeParam()},wet:{gain:fakeParam()}};
  const targets=[
    {sectionId:"a",start:0,end:10,delayMs:180,wet:.18,feedback:.25,lowpassHz:6500,transitionSeconds:2,curve:"smooth"},
    {sectionId:"b",start:10,end:20,delayMs:180,wet:0,feedback:.25,lowpassHz:6500,transitionSeconds:3,curve:"smooth"}
  ];
  scheduleSectionEcho(stage,targets,0,1,24);
  const wetRamps=stage.wet.gain.calls.filter(row=>row[0]==="ramp");
  assert.ok(wetRamps.some(row=>row[2]===14&&Math.abs(row[1])<1e-8));
  assert.ok(wetRamps.some(row=>row[1]>.1));
  const second={delay:{delayTime:fakeParam()},feedback:{gain:fakeParam()},
    filter:{frequency:fakeParam()},wet:{gain:fakeParam()}};
  scheduleSectionEcho(second,targets,12,100,24);
  const current=second.wet.gain.calls.find(row=>row[0]==="set");
  assert.ok(current[1]>=0&&current[1]<.18);
  assert.equal(current[2],100);
});
