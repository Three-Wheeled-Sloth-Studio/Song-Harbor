import type {AudioFinding} from "./AudioCleanupAnalyzer";

// Identifies a finding across correction previews and analyzer refreshes.
// This matches the analyzer's stable time resolution (10 ms).
export function findingReviewKey(finding:Pick<AudioFinding,"kind"|"timeSeconds">):string{
  return finding.kind+":"+finding.timeSeconds.toFixed(2);
}
export function markReviewed(previous:ReadonlySet<string>,key:string):Set<string>{
  const next=new Set(previous);
  next.add(key);
  return next;
}
export function toggleReviewed(previous:ReadonlySet<string>,key:string):Set<string>{
  const next=new Set(previous);
  if(next.has(key))next.delete(key);else next.add(key);
  return next;
}
