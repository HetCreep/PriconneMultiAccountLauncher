This is a maintenance release. It makes in-place updates smoother: the installer now closes the running launcher for you instead of stopping with a "could not close applications" prompt.

## Highlights & Fixes

- **Updating no longer stalls on "Setup was unable to automatically close all applications"**:
  - When you run the installer while the launcher is still open, Setup now closes the running app automatically and continues. Previously the wizard could stall, because the packaged (PyInstaller, windowless) app did not respond to the Windows Restart Manager's graceful-close request.
  - This forced close is safe: account switching is registry-only and the launcher restores its baseline on the next start (crash-recovery path), so an interrupted session never corrupts account state.

## Build & Distribution

- Builds run entirely in GitHub Actions on every version tag. Local builds are not distributed.
- Each release publishes the installer, a portable `.zip`, `SHA256SUMS.txt`, and an SBOM (`sbom.cdx.json`). Older releases are removed automatically so only the latest installer is offered.

## Compatibility

- Windows 10 1809+ / Windows 11, 64-bit.
- Requires Princess Connect! Re:Dive installed via DMM Game Player.
- Japan-region access (DMM is region-locked) — set a JP proxy/VPN in Settings → Advanced if needed.

## Upgrade Notes

- No action required. Existing accounts and shortcuts are preserved.
- If you upgrade from v6.3.35 with the launcher still running, just continue through the installer — it now closes and relaunches the app for you.
