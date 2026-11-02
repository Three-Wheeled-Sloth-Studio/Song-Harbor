import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
const mixer=fs.readFileSync(new URL("../src/StemMixer.tsx",import.meta.url),"utf8");
const tools=fs.readFileSync(new URL("../src/WorkbenchTools.tsx",import.meta.url),"utf8");
test("download rail and footer both reach one shared export options tool",()=>{
  assert.match(tools,/id:"download".*label:"Download"/);
  assert.match(mixer,/tool==="download"&&<div className="song-tool-handoff song-download-options"/);
  assert.match(mixer,/<IconButton icon="⇩" label="Download options"/);
  assert.match(mixer,/setOpenTools\(existing=>existing\.includes\("download"\)\?existing:\[\.\.\.existing,"download"\]\)/);
});
test("same download tool offers rendered full mix, source stem files, and aligned multitrack export",()=>{
  const start=mixer.indexOf('{tool==="download"&&');
  const end=mixer.indexOf('</ToolWindow>',start);
  assert.ok(start>=0&&end>start);
  const panel=mixer.slice(start,end);
  assert.match(panel,/exportMix\(\)/);
  assert.match(panel,/href=\{mixUrl\}/);
  assert.match(panel,/files\.map\(filename=>/);
  assert.match(panel,/\/api\/jobs\//);
  assert.match(panel,/setDawOpen\(true\)/);
  assert.doesNotMatch(panel,/window\.open\(/);
});
test("second download button does not directly render or bypass export checks",()=>{
  const footer=mixer.slice(mixer.indexOf('<div className="song-production-exports">'));
  assert.doesNotMatch(footer,/onClick=\{\(\)=>\{void exportMix\(\);\}\}/);
  assert.match(mixer,/if\(correction\|\|sectionPreviewActive\)/);
  assert.match(mixer,/MixHeadroomError/);
});
