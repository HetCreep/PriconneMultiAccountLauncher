This release reworks account switching to be lightweight and crash-safe, and fixes installer/brand collisions with the upstream project. Multi-GB re-downloads and black-screen renders when switching accounts are gone.

## Highlights & Fixes

- **Account switch is now registry-only**:
  - Switching accounts swaps only the Cygames registry binding. The shared asset cache (`manifest.db`, `a/ b/ m/ s/ v/`) is never touched, so you no longer get a 10+ GB re-download or black textures after a switch — only the game's normal small per-account delta.
- **Your primary DMM account is preserved**:
  - The state you had before using the launcher is snapshotted as a baseline and restored automatically after each launched session closes, so launching the official DMM Game Player directly keeps working.
- **Crash recovery**:
  - If the launcher is force-killed (Task Manager, power loss) mid-session, the next launch detects the stale state and restores the baseline before continuing — no more "this game data is linked to another PC account" after an unclean exit.
- **Separate from upstream DMMGamePlayerFastLauncher**:
  - The installer now uses a unique AppId and refuses to install into a directory that belongs to the upstream project. Installing or uninstalling one no longer corrupts the other, and the upstream binary is never deleted or modified by us.
- **Browser import no longer pops the DMM client mid-import**:
  - The OAuth success page is stopped before it can hand off to `dmmgameplayer://`, so importing an account stays inside the import flow.
- **Forms refresh after save**:
  - Creating a shortcut or importing an account clears the form and re-scans accounts automatically — no manual restart to see new entries.
- **Smart scrollbar**:
  - Tabs that fit on screen no longer show an unnecessary scrollbar.

## Build & Distribution

- Builds now run entirely in GitHub Actions on every version tag. Local builds are not distributed.
- Each release publishes the installer, a portable `.zip`, `SHA256SUMS.txt`, and an SBOM. Older releases are removed automatically so only the latest installer is offered.

## Compatibility

- Windows 10 1809+ / Windows 11, 64-bit.
- Requires Princess Connect! Re:Dive installed via DMM Game Player.
- Japan-region access (DMM is region-locked) — set a JP proxy/VPN in Settings → Advanced if needed.

## Upgrade Notes

- No action required. Existing accounts and shortcuts are preserved.
- Account snapshots created by older builds are harmless; the launcher re-captures a clean baseline on first launch of this version.
