import {inspectRenderedAudio,type AudioFinding} from "./AudioCleanupAnalyzer.ts";

export type StemIntegrityResult={key:string;filename:string;startSeconds:number;findings:readonly AudioFinding[]};
type AudioLike=Pick<AudioBuffer,"length"|"sampleRate"|"numberOfChannels"|"getChannelData">;

/** Read-only per-source analysis; timestamps are expressed on the song timeline. */
export function scanStemSource(key:string,filename:string,startSeconds:number,
  buffer:AudioLike,maxFindings=12):StemIntegrityResult{
  if(!Number.isFinite(startSeconds)||startSeconds<0)throw Error("Invalid source timeline offset");
  const findings=inspectRenderedAudio(buffer,0,maxFindings).map(finding=>({
    ...finding,timeSeconds:finding.timeSeconds+startSeconds,sources:[key]
  }));
  return {key,filename,startSeconds,findings};
}
