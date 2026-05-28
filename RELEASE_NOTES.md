This release fixes a false "update available" notification, and changes how older releases are published so nobody installs a stale build.

## Highlights & Fixes

- **No more false "update available" prompt**:
  - The in-app update check now compares semantic versions (`latest > current`) instead of a plain string match. Previously a stale update-check cache (kept across upgrades) could keep showing "a new version is available" even when you were already on the newest build.

## Build & Distribution

- Builds run entirely in GitHub Actions on every version tag. Local builds are not distributed.
- The latest release ships the installer, a portable `.zip`, `SHA256SUMS.txt`, and an SBOM (`sbom.cdx.json`).
- **Older releases keep only their source code** — their installers are removed automatically, so everyone installs the current build while the full version history and source stay available for audit.

## Compatibility

- Windows 10 1809+ / Windows 11, 64-bit.
- Requires Princess Connect! Re:Dive installed via DMM Game Player.
- Japan-region access (DMM is region-locked) — set a JP proxy/VPN in Settings → Advanced if needed.

## Upgrade Notes

- No action required. Existing accounts and shortcuts are preserved.
- If v6.3.36 still showed a false "update available" toast, this build clears it. (You can also delete `data\update_check_cache.json` to refresh immediately.)
