# Isolated Song Harbor dev channel

**Default development branch remains `main`.** Use `dev` only when a risky change is explicitly designated for experimental testing. No routine work should land on dev.

## Install and launch

From the standard `main` source checkout, run:

```bat
scripts\launch-song-harbor-dev.bat
```

On the first run it clones `origin/dev` beside the production checkout and bootstraps a separate runtime if needed. With the normal Windows paths:

- Production source: `D:\Apps\Song-Harbor` (`main`)
- Dev source: `D:\Apps\Song-Harbor-Dev` (`dev`)
- Production runtime: `D:\Apps\SongHarbor`
- Dev runtime: `D:\Apps\SongHarborDev`

These are examples; source location is derived from wherever the main checkout is installed. To override the isolated dev runtime path:

```bat
scripts\launch-song-harbor-dev.bat E:\Apps\SongHarborDev
```

The separate runtime prevents test projects, installed dependencies, cache and user settings from modifying production state. This may require a first-run dependency install; model files are not copied or automatically shared. Keep free storage in mind.

## Updates and refresh

The dev launcher executes the existing `scripts/start-song-harbor.ps1` **inside the dev checkout**. That runs `update-checkout.ps1`, which resolves the current branch and safely fast-forwards `origin/dev`. The in-app update/relaunch also discovers the active checkout branch and pulls `origin/dev` for a dev instance. It does not change the main checkout.

The production launcher remains `scripts/launch-song-harbor.bat` from the main checkout and continues to pull `origin/main`.

## Guardrails

- The dev launcher refuses to switch the main checkout's branch.
- An existing dev checkout must already be on branch `dev`, with the matching origin; no auto-reset, stash or forced checkout.
- The dev runtime must not point to the production runtime, either source checkout, or the configured `SONG_HARBOR_HOME`.
- Normal main development and its launch/update mechanisms are unchanged.
- Do not run production and dev simultaneously for GPU-heavy models; resource contention can lock up the host.
- Branch creation alone is infrastructure; no feature development belongs on dev until explicitly chosen.
