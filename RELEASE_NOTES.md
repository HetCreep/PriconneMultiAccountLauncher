This is a security and reliability release. It hardens account switching and backup import, and stops several ways a log or error window could expose sensitive data.

## Highlights & Fixes

- **Account switching no longer loses your saved state.** A failed backup, a failed restore, or a failed write of the "active account" marker now stops the switch and puts the previous state back, instead of carrying on and overwriting your game binding. Two launcher windows switching accounts at the same moment are now serialized. Your own DMM client login is restored even if the game fails to start.
- **Importing a backup (`.pmal`) is safer.** A backup file from someone else can no longer write outside the launcher's data folder, run commands through a crafted shortcut name, point an account at another folder, or inflate into a huge file. The launcher's internal `_baseline_` snapshot cannot be imported, renamed or deleted as if it were an account.
- **Logs and error windows no longer leak credentials.** Redaction now fails closed, covers exception tracebacks, quoted hardware-ID fields and `user:password@` in proxy addresses, and always applies to the debug window (the "mask token" option is gone: it implied tokens were shown when it was off).
- **Game and client downloads are checked.** A failed download (for example an expired signed link) is no longer written into your game files and recorded as the installed version, and a server-supplied path can no longer escape the game folder.
- **Removing a proxy in Settings takes effect immediately** instead of continuing to route requests until you restart.
- **Renaming or deleting an account** now moves or removes its saved game binding too, and is refused while that account is the active one.
- `DMMGamePlayer.exe` is launched by its full path.
- Release downloads: `SHA256SUMS.txt` and the SBOM now stay attached to every older release, so a copy you downloaded earlier can still be verified.

## Upgrade Notes

- Existing accounts and shortcuts are preserved.
- A backup is now rejected as a whole if an entry name contains a dot, `$`, a backtick or `;`, or is reserved. The error names the entry. Account names with a dot never worked reliably, because the launcher derives file names from them.
- New installs default to `%LOCALAPPDATA%\Programs`; existing installs upgrade in place.

## Security

- Several issues found by code review and a security scan are fixed. Report vulnerabilities privately through GitHub Security Advisories, not the public tracker — see `SECURITY.md`.

## Build & Distribution

- Builds run entirely in GitHub Actions on every version tag. Local builds are not distributed.
- Each release ships the installer, a portable `.zip`, `SHA256SUMS.txt`, and an SBOM. Older releases keep their source code, `SHA256SUMS.txt` and SBOM; only the installable binaries are removed.
- The release is now gated on automated tests and a dependency vulnerability audit.

## Known Issues

- Binaries are not code-signed; SmartScreen will warn about an unknown publisher. Verify the SHA-256 in the Verification section below before running.

## Compatibility

- Windows 10 1809+ / Windows 11, 64-bit.
- Requires Princess Connect! Re:Dive installed via DMM Game Player.
- Japan-region access (DMM is region-locked) — set a JP proxy/VPN in Settings → Advanced if needed.
