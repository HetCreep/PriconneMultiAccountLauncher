This release is internal security hardening for the local logging and credential-storage paths. No user-facing behavior changes.

## Highlights & Fixes

- **Log redaction now covers all log outputs**:
  - The credential-redaction filter is now attached to every log handler (file, console, debug window), not just the root logger. Previously, log lines emitted by submodules could reach the log file before redaction ran. Tokens, cookies, and hardware identifiers are now stripped on every output.
- **Log-injection hardening**:
  - Carriage-return / line-feed / tab characters in logged values are now encoded, so data from external sources can't forge fake log lines.
- **DPAPI calls hardened**:
  - Windows credential encrypt/decrypt now passes `CRYPTPROTECT_UI_FORBIDDEN`, ensuring no unexpected prompt can appear, and continues to use the current-user scope only (never machine scope).

## Build & Distribution

- Builds run entirely in GitHub Actions on every version tag. Local builds are not distributed.
- The latest release ships the installer, a portable `.zip`, `SHA256SUMS.txt`, and an SBOM. Older releases keep only their source code.

## Compatibility

- Windows 10 1809+ / Windows 11, 64-bit.
- Requires Princess Connect! Re:Dive installed via DMM Game Player.
- Japan-region access (DMM is region-locked) — set a JP proxy/VPN in Settings → Advanced if needed.

## Upgrade Notes

- No action required. Existing accounts and shortcuts are preserved.
