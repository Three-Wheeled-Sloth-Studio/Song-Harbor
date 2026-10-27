import {pathToFileURL} from "node:url";
import {resolve} from "node:path";
import {inspectReverbTail} from "../src/ReverbTailDiagnostic.ts";
import {plannedMethodFixtures} from "./planned-artifact-fixtures.mjs";
import {summarizeArtifactCases} from "./artifact-evaluation.mjs";

export function runReverbTailBenchmark(){
  const cases=plannedMethodFixtures().reverb.map(item=>({
    id:item.id,category:item.category,
    expectedEvents:item.annotations.map(({timeSeconds})=>({timeSeconds})),
    observations:inspectReverbTail(item.audio).map(({timeSeconds,kind})=>({timeSeconds,kind}))
  }));
  return {method:"reverb-tail-envelope-v1",dataset:"deterministic-synthetic-v1",
    createdBy:"Song Harbor offline fixture harness",
    interpretation:"Acoustic evidence only; cutoff PCM is identical to the intentional gate control.",
    ...summarizeArtifactCases(cases,.05)};
}
if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
  process.stdout.write(JSON.stringify(runReverbTailBenchmark(),null,2)+"\n");
}
