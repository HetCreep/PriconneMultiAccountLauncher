This release stops the DMM Game Player window from popping up (and hanging blank) when the launcher refreshes an expired login through your browser.

## Highlights & Fixes

- **No more stray, blank DMM Game Player window during browser re-login**:
  - When a shortcut launch needed to refresh an expired session via the browser, the DMM login "success" page would redirect to `dmmgameplayer://`, which opened the DMM Game Player client — often as a blank window you had to close by hand. The game itself launched fine; the window was just noise.
  - The launcher now blocks the `dmmgameplayer://` external-protocol launch at the browser level (Chrome/Edge/Firefox), in addition to the existing page-stop guard. The success page can no longer pop the DMM client. Your game launch is unaffected.

## Build & Distribution

- Builds run entirely in GitHub Actions on every version tag. Local builds are not distributed.
- The latest release ships the installer, a portable `.zip`, `SHA256SUMS.txt`, and an SBOM. Older releases keep only their source code.

## Compatibility

- Windows 10 1809+ / Windows 11, 64-bit.
- Requires Princess Connect! Re:Dive installed via DMM Game Player.
- Japan-region access (DMM is region-locked) — set a JP proxy/VPN in Settings → Advanced if needed.

## Upgrade Notes

- No action required. Existing accounts and shortcuts are preserved.
