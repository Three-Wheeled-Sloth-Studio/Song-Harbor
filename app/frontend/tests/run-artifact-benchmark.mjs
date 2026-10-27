import {inspectAttackRise} from "../src/AttackRiseDiagnostic.ts";
import {attackRiseFixtures} from "./artifact-fixtures.mjs";
import {summarizeArtifactCases} from "./artifact-evaluation.mjs";

/** Run with: node --experimental-strip-types app/frontend/tests/run-artifact-benchmark.mjs
 * Writes JSON to stdout. Does not claim clinical, perceptual or external validity.
 */
export function runAttackRiseBenchmark(){
  const cases=attackRiseFixtures().map(item=>({
    id:item.id,category:item.category,expectedEvents:item.expectedEvents,
    observations:inspectAttackRise(item.audio).map(({timeSeconds,riseMs,peakRms})=>({timeSeconds,riseMs,peakRms}))
  }));
  return {method:"attack-rise-rms-v1",dataset:"deterministic-synthetic-v1",
    createdBy:"Song Harbor offline fixture harness",
    ...summarizeArtifactCases(cases,.05)};
}
if(process.argv[1]&&import.meta.url===new URL("file://"+process.argv[1].replaceAll("\\","/")).href){
  process.stdout.write(JSON.stringify(runAttackRiseBenchmark(),null,2)+"\n");
}
