# ACE backing-vocal freeze incident and recovery requirements (2026-10-28)

## Incident report
During the first Everybody Hums the Signal backing-hum experiment, the user reported that the ACE model made Windows unresponsive, remained unresponsive, and required a reboot. No successful candidate or verified runtime metrics were reported. Do not claim that OOM is confirmed.

## Immediate containment
- Block `backing_vocals` Lego generation in both the UI and server. No additional backing-hum GPU testing until safety measures pass locally.
- Do not delete saved candidates or original project stems.
- Record that generation section selectors displayed raw seconds such as 82.4s instead of the established m:ss.mmm timeline; format timeline positions consistently while leaving relative context durations in seconds.

## Required before re-enabling
1. **Preflight and model resource policy:** capture free/total GPU VRAM and system memory, currently loaded models, known ACE process ownership, expected context length, and conservative minimum headroom. Fail closed if metrics are unavailable or thresholds are not met.
2. **Emergency stop independent of the generation job:** Song Harbor currently refuses ACE stop during active candidate generation. Add a protected emergency-stop path for Song Harbor-owned ACE only, not arbitrary pre-existing ACE processes. Kill the owned process tree when needed; mark the active candidate failed/interrupted and retain diagnostics and source recordings.
3. **Watchdog beyond the browser:** detect non-responsive ACE health/polling and process exit, cap jobs to a measured safe duration, and reclaim owned GPU resources. An HTTP timeout alone does not stop GPU work. Test the Windows child process tree and released VRAM.
4. **Crash/forced reboot recovery:** reconcile durable candidate states left in generating/processing after restart, retain logs, and avoid permanently blocking Stop because of stale candidate records.
5. **Conservative smoke ladder:** unloaded ACE baseline -> small Base model health/preflight -> short isolated instrumental test -> 5-8s backing-vocal attempt only after safeguards pass. Track GPU peak, system RAM, driver behavior, and recovery.
6. **Timecode UX:** display all absolute song positions as m:ss.mmm throughout generation selectors, preview positioning, history, and acceptance; retain seconds for context-before/after and pre-roll durations.

## Evidence / hypothesis
Previous ACE benchmark recorded >10 GiB GPU allocation on an RTX 4070 12 GiB, which suggests possible resource pressure but does not establish the freeze cause. Review ACE log, Windows Reliability Monitor and GPU/CPU/memory measurements if available. Avoid requesting another uncontrolled reproduction.

## Acceptance criteria
- System remains interactive under generation load.
- Emergency stop is independently callable while job is active and releases the owned ACE process resources.
- Stale jobs reconcile on restart.
- Preflight rejects unsafe jobs and explains why.
- Timecode matches section editor format.
