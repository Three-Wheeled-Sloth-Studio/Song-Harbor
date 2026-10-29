/** Convert a Song Harbor whole-song sheet into lyrics-only model prompt text.
 * This is an export, not a round-trip editable Song Harbor script.
 */
export type LyricExportFormat="yue2"|"ace";
const SECTION=/^\[(Intro|Verse|Pre-Chorus|Chorus|Bridge|Instrumental|Guitar Solo|Outro|End)(?:\s+(\d{1,2}))?(?:\s+.*)?\]$/;
const TIME=/\d{1,3}:\d{2}(?:\.\d{1,3})?\s*-\s*\d{1,3}:\d{2}(?:\.\d{1,3})?/;
function sectionTag(line:string,format:LyricExportFormat):string {
  const m=SECTION.exec(line);
  if(!m)throw Error("Unrecognized section header: "+line);
  // Reject trailing unrelated material rather than silently feeding Song Harbor
  // spatial directives or invalid metadata into a generation model.
  const rest=line.slice(1+m[1].length+(m[2]?" "+m[2]:"").length,-1).trim();
  if(rest&&!TIME.test(rest)&&!/^\w[\w-]*:/.test(rest))
    throw Error("Cannot convert section header: "+line);
  const kind=m[1]==="Guitar Solo"?"Instrumental":m[1];
  const number=m[2]&&(format==="ace"||kind==="Verse")?" "+m[2]:"";
  return "["+kind+number+"]";
}
export function exportSongLyrics(sheet:string,format:LyricExportFormat):string {
  if(format!=="yue2"&&format!=="ace")throw Error("Unknown lyric export format");
  const output:string[]=[];
  let insideProduction=false;
  let sections=0;
  for(const original of sheet.replace(/\r\n?/g,"\n").split("\n")){
    const line=original.trim();
    if(!line){if(output.length&&output[output.length-1]!=="")output.push("");continue;}
    if(insideProduction){
      if(line.includes("}")){
        if(!line.endsWith("}")||line.slice(0,-1).includes("}"))
          throw Error("Production block must end at the closing brace");
        insideProduction=false;
      }
      continue;
    }
    if(line.startsWith("#"))continue;
    if(line.startsWith("{")){
      if(!line.includes("}"))insideProduction=true;
      else if(!line.endsWith("}")||line.slice(0,-1).includes("}"))
        throw Error("Invalid production block");
      continue;
    }
    if(line.startsWith("[")&&line.endsWith("]")){
      const tag=sectionTag(line,format);
      if(output.length&&output[output.length-1]!=="")output.push("");
      output.push(tag);
      sections++;
      continue;
    }
    if(line.startsWith("}")||line.includes("}"))throw Error("Unexpected production block ending");
    if(!sections)throw Error("Lyrics must follow a section header");
    // YuE2 accepts a deliberately narrow set of structural tags. Its style/
    // direction information belongs in the separate song-level style/ABC prompt.
    // ACE preserves stage directions as plain parenthetical text.
    if(format==="yue2"&&/^\([^\n]*\)$/.test(line))continue;
    output.push(original.trimEnd());
  }
  if(insideProduction)throw Error("Unclosed Song Harbor production block");
  if(!sections)throw Error("No song sections to export");
  return output.join("\n").trim()+"\n";
}
