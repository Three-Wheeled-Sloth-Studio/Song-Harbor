import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import ts from "typescript";
const source=fs.readFileSync(new URL("../src/EchoDelay.ts",import.meta.url),"utf8");
const js=ts.transpileModule(source,{compilerOptions:{
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext
}}).outputText;
const {validateEcho,echoTailSeconds}=await import(
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
