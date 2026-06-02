This is a small maintenance release. It relaxes how often the app checks for updates — this is a stable desktop tool, not a browser, so a daily check was unnecessary.

## Highlights & Fixes

- **Update check is now weekly instead of daily**:
  - The notify-only update check now reuses its cached result for 7 days (was 24 hours). Releases are infrequent, so this is plenty to surface a new version while cutting background GitHub API traffic. You can still disable the check entirely in Settings → Advanced.

## Build & Distribution

- Builds run entirely in GitHub Actions on every version tag. Local builds are not distributed.
- The latest release ships the installer, a portable `.zip`, `SHA256SUMS.txt`, and an SBOM (`sbom.cdx.json`). Older releases keep only their source code — their installers are removed automatically.

## Compatibility

- Windows 10 1809+ / Windows 11, 64-bit.
- Requires Princess Connect! Re:Dive installed via DMM Game Player.
- Japan-region access (DMM is region-locked) — set a JP proxy/VPN in Settings → Advanced if needed.

## Upgrade Notes

- No action required. Existing accounts and shortcuts are preserved.
